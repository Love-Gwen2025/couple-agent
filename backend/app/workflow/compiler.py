from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from loguru import logger

from app.agent.graph import create_context_aware_chatbot_node
from app.nodes.context_node import get_history_context, get_kb_context
from app.utils.content import extract_text_content
from app.workflow.definition import WorkflowNode
from app.workflow.state import WorkflowState
from app.workflow.validation import ValidatedWorkflow


def _llm_tools_condition(state: WorkflowState) -> str:
    """
    条件路由：决定下一步是执行工具还是继续到 next。
    """
    messages = state.get("messages", [])
    if not messages:
        return "__next__"

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        logger.info(f"🔧 Tool calls detected: {[tc['name'] for tc in last_message.tool_calls]}")
        return "tools"

    return "__next__"


def _create_passthrough_node():
    return lambda state: state


def _create_router_node(model, node: WorkflowNode, cases: list[str]):
    async def router_node(state: WorkflowState, _: RunnableConfig | None = None) -> dict[str, Any]:
        config = node.config or {}
        strategy = config.get("strategy", "field")

        if strategy == "field":
            field = config.get("field")
            if not field:
                raise ValueError("router.strategy=field 时必须配置 field")
            value = state.get(field)
            if value is None:
                default_case = config.get("defaultCase")
                if default_case:
                    return {"route": default_case}
                raise ValueError(f"router.field={field} 在 state 中不存在")
            value_str = str(value)
            if value_str in cases:
                return {"route": value_str}
            default_case = config.get("defaultCase")
            if default_case:
                return {"route": default_case}
            raise ValueError(f"router 无法匹配 case（value={value_str}）")

        if strategy == "llm":
            instruction = config.get("prompt") or "请选择最合适的分支。"
            case_list = ", ".join(cases)
            prompt = (
                f"{instruction}\n\n"
                f"可选分支（只输出其中一个分支标签，不要输出其他内容）:\n{case_list}\n\n"
                "分支标签:"
            )
            from langchain_core.messages import HumanMessage, SystemMessage

            resp = await model.ainvoke([SystemMessage(content="你是一个路由器。"), HumanMessage(content=prompt)])
            selected = extract_text_content(resp.content).strip()
            if selected in cases:
                return {"route": selected}
            default_case = config.get("defaultCase")
            if default_case:
                return {"route": default_case}
            raise ValueError(f"router LLM 输出不合法（{selected}），可选: {cases}")

        raise ValueError(f"不支持的 router.strategy: {strategy}")

    return router_node


def _create_context_node(settings, node: WorkflowNode):
    async def context_node(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
        cfg = node.config or {}
        enable_history = bool(cfg.get("enableHistory", True))
        enable_kb = bool(cfg.get("enableKnowledgeBase", True))

        # 提取用户查询（取最后一条 HumanMessage）
        from langchain_core.messages import HumanMessage

        query = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                query = extract_text_content(msg.content)
                break

        if not query:
            return {"history_context": "", "kb_context": ""}

        configurable = config.get("configurable", {})
        embedding_service = configurable.get("embedding_service")
        db_session = configurable.get("db_session")
        conversation_id = configurable.get("conversation_id")

        history_context = ""
        kb_context = ""

        if enable_history:
            history_context = await get_history_context(
                query=query,
                embedding_service=embedding_service,
                db_session=db_session,
                conversation_id=conversation_id,
                top_k=settings.rag_top_k,
                similarity_threshold=settings.rag_similarity_threshold,
            )

        if enable_kb:
            kb_context = await get_kb_context(
                query=query,
                embedding_service=embedding_service,
                db_session=db_session,
                knowledge_base_ids=state.get("knowledge_base_ids", []),
                top_k=settings.rag_top_k,
                similarity_threshold=settings.rag_similarity_threshold,
            )

        return {"history_context": history_context, "kb_context": kb_context}

    return context_node


def compile_validated_workflow(
    validated: ValidatedWorkflow,
    *,
    model,
    tools: list[BaseTool],
    checkpointer,
    settings,
):
    """
    将已校验的 WorkflowDefinition 编译为 LangGraph 可执行图。

    返回：
    - compiled graph
    - output_llm_node_id（用于 SSE 过滤 token 输出）
    """
    model_with_tools = model.bind_tools(tools) if tools else model
    tool_node = ToolNode(tools) if tools else None

    workflow = StateGraph(WorkflowState)

    # 1) 添加节点
    for node in validated.definition.nodes:
        if node.type in {"start", "end"}:
            workflow.add_node(node.id, _create_passthrough_node())
        elif node.type == "router":
            outgoing = validated.edges_by_source.get(node.id, [])
            cases = [e.case for e in outgoing if e.case]
            workflow.add_node(node.id, _create_router_node(model, node, cases))
        elif node.type == "context":
            workflow.add_node(node.id, _create_context_node(settings, node))
        elif node.type == "llm":
            workflow.add_node(node.id, create_context_aware_chatbot_node(model_with_tools))
        elif node.type == "verify":
            # MVP：先做透传，避免引入额外 LLM 回合与输出语义复杂度
            workflow.add_node(node.id, _create_passthrough_node())
        else:
            raise ValueError(f"未知节点类型: {node.type}")

    if tool_node:
        workflow.add_node("__tools__", tool_node)

    # 2) 入口
    workflow.set_entry_point(validated.start_node_id)

    # 3) 边
    for node in validated.definition.nodes:
        outgoing = validated.edges_by_source.get(node.id, [])

        if node.type == "end":
            workflow.add_edge(node.id, END)
            continue

        if node.type == "router":
            mapping = {e.case: e.target for e in outgoing}  # case 已在校验阶段保证非空且唯一
            workflow.add_conditional_edges(
                node.id,
                lambda state: state.get("route"),
                mapping,
            )
            continue

        # 非 router 节点：恰好 1 条出边（已校验）
        next_node_id = outgoing[0].target if outgoing else None
        if not next_node_id:
            raise ValueError(f"节点缺少出边: {node.id}")

        if node.type == "llm" and tool_node:
            workflow.add_conditional_edges(
                node.id,
                _llm_tools_condition,
                {"tools": "__tools__", "__next__": next_node_id},
            )
            workflow.add_edge("__tools__", node.id)
        else:
            workflow.add_edge(node.id, next_node_id)

    return workflow.compile(checkpointer=checkpointer), validated.llm_node_id

