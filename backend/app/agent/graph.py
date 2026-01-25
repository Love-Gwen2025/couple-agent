"""
LangGraph Agent 构建模块 (v4 - 知识库集成架构)

新架构支持两种模式，均集成知识库 RAG：

1. 普通对话模式 (mode="chat"):
   START → router → rewrite → context_retrieval → chatbot → [tools → chatbot]* → END

   context_retrieval 节点并行执行：
   - 获取历史对话上下文
   - 获取知识库上下文

2. 深度搜索模式 (mode="deep_search"):
   START → router → kb_precheck → planning → [search → planning]* → summary → END

   kb_precheck 节点：
   - 在规划前检索内部知识库
   - 将已知信息注入 references，避免重复搜索

支持：
- checkpoint_id 分支（时间旅行）
- 工具自主调用（模型决定是否调用）
- DeepSearch 多轮搜索规划
- 知识库 RAG 混合检索
"""

from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from loguru import logger
from typing_extensions import TypedDict

from app.nodes.context_node import create_context_node
from app.nodes.kb_precheck_node import create_kb_precheck_node
from app.nodes.planning_node import create_planning_node
from app.nodes.rewrite_node import create_rewrite_node
from app.nodes.search_node import create_search_node
from app.nodes.summary_node import create_summary_node

# ========== 1. 定义 Agent 状态 ==========


class AgentState(TypedDict):
    """
    Agent 的状态定义 (v4 - 知识库集成)。

    Attributes:
        messages: 对话消息历史（使用 add_messages reducer 自动追加）
        mode: 对话模式 ("chat" | "deep_search")

        # 知识库相关
        knowledge_base_ids: 启用的知识库 ID 列表
        history_context: 历史对话上下文（context_node 输出）
        kb_context: 知识库上下文（context_node / kb_precheck 输出）

        # DeepSearch 专用字段
        question: 用户原始问题
        search_queries: 待搜索的关键词列表
        references: 累积的参考资料 {query: [results]}
        planning_rounds: 当前规划轮次

    注意：内部依赖（embedding_service, db_session, conversation_id）
    通过 config['configurable'] 传递，而非放在 state 中，
    以避免 LangGraph checkpoint 序列化问题。
    """

    messages: Annotated[list[AnyMessage], add_messages]
    mode: str

    # 知识库相关
    knowledge_base_ids: list[int]
    history_context: str
    kb_context: str

    # DeepSearch 专用字段
    question: str
    search_queries: list[str]
    references: dict[str, list[str]]
    planning_rounds: int


# ========== 2. 路由逻辑 ==========


def mode_router(state: AgentState) -> Literal["rewrite", "kb_precheck"]:
    """
    入口路由：根据 mode 决定进入普通对话还是深度搜索。

    Chat Mode → rewrite（然后 context_retrieval）
    DeepSearch Mode → kb_precheck（然后 planning）
    """
    mode = state.get("mode", "chat")
    if mode == "deep_search":
        logger.info("🔬 Entering DeepSearch mode")
        return "kb_precheck"
    else:
        logger.info("💬 Entering Chat mode")
        return "rewrite"


def tools_condition(state: AgentState) -> Literal["tools", "__end__"]:
    """
    条件路由：决定下一步是执行工具还是结束。
    """
    messages = state["messages"]
    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        logger.info(f"🔧 Tool calls detected: {[tc['name'] for tc in last_message.tool_calls]}")
        return "tools"

    logger.debug("No tool calls, ending conversation")
    return "__end__"


def planning_router(state: AgentState) -> Literal["search", "summary"]:
    """
    DeepSearch 规划路由：决定是继续搜索还是进入总结。
    """
    from app.core.settings import get_settings

    settings = get_settings()
    max_rounds = settings.deep_search_max_rounds

    planning_rounds = state.get("planning_rounds", 0)
    search_queries = state.get("search_queries", [])

    # 超过最大轮次，强制进入总结
    if planning_rounds >= max_rounds:
        logger.warning(f"⚠️ Max planning rounds ({max_rounds}) reached, forcing summary")
        return "summary"

    # 有搜索词，继续搜索
    if search_queries:
        logger.info(f"🔍 Search queries: {search_queries}")
        return "search"

    # 无搜索词，进入总结
    logger.info("✅ No more queries, proceeding to summary")
    return "summary"


# ========== 3. 上下文增强的 Chatbot 节点 ==========


def _build_context_prompt(history_context: str, kb_context: str) -> str | None:
    """
    构建上下文提示词

    Args:
        history_context: 历史对话上下文
        kb_context: 知识库上下文

    Returns:
        合并后的上下文字符串，无内容时返回 None
    """
    context_parts = []
    if kb_context:
        context_parts.append(kb_context)
    if history_context:
        context_parts.append(history_context)

    return "\n\n".join(context_parts) if context_parts else None


def _find_system_message_insert_index(messages: list) -> int:
    """
    查找系统消息的插入位置（在第一个 SystemMessage 之后）

    Args:
        messages: 消息列表

    Returns:
        插入索引位置
    """
    for i, m in enumerate(messages):
        if isinstance(m, SystemMessage):
            return i + 1
    return 0


def _inject_context_message(messages: list, context_prompt: str) -> list:
    """
    将上下文注入到消息列表中

    Args:
        messages: 原始消息列表
        context_prompt: 上下文提示词

    Returns:
        注入上下文后的消息列表（新列表）
    """
    # 检查是否已有上下文系统消息
    has_context = any(
        isinstance(m, SystemMessage) and getattr(m, "id", None) == "sys_context" for m in messages
    )

    if has_context:
        return messages

    # 创建上下文消息并插入
    context_message = SystemMessage(
        content=f"以下是与用户问题相关的参考资料，请在回答时参考：\n\n{context_prompt}",
        id="sys_context",
    )
    insert_idx = _find_system_message_insert_index(messages)
    new_messages = list(messages)
    new_messages.insert(insert_idx, context_message)
    return new_messages


def create_context_aware_chatbot_node(model):
    """
    创建上下文感知的 Chatbot 节点

    该节点会将 history_context 和 kb_context 注入到系统提示中，
    让模型在回答时参考这些上下文信息。

    Args:
        model: 绑定了工具的 LangChain 模型实例

    Returns:
        节点函数
    """

    async def chatbot_node(state: dict[str, Any]) -> dict[str, list]:
        """
        上下文感知的 Chatbot 节点

        输入 state:
          - messages: 消息列表
          - history_context: 历史对话上下文
          - kb_context: 知识库上下文

        输出 state:
          - messages: 追加 AI 响应
        """
        messages = list(state.get("messages", []))
        history_context = state.get("history_context", "")
        kb_context = state.get("kb_context", "")

        logger.info(f"🤖 Context-aware Chatbot receiving {len(messages)} messages")
        logger.info(f"📜 History context: {len(history_context)} chars")
        logger.info(f"📚 KB context: {len(kb_context)} chars")

        # 构建并注入上下文
        context_prompt = _build_context_prompt(history_context, kb_context)
        if context_prompt:
            messages = _inject_context_message(messages, context_prompt)

        response = await model.ainvoke(messages)

        # 记录响应信息
        has_tool_calls = bool(response.tool_calls) if hasattr(response, "tool_calls") else False
        content_len = len(response.content) if response.content else 0
        logger.info(
            f"🤖 Chatbot response: has_tool_calls={has_tool_calls}, content_len={content_len}"
        )

        if has_tool_calls:
            logger.info(f"🔧 Tool calls: {[tc['name'] for tc in response.tool_calls]}")

        return {"messages": [response]}

    return chatbot_node


# ========== 4. 构建统一 Agent 图 ==========


def create_agent_graph(
    model: ChatOpenAI,
    tools: list[BaseTool],
    checkpointer=None,
    enable_rewrite: bool = True,
) -> StateGraph:
    """
    创建 LangGraph Agent 工作流 (v4 - 知识库集成)。

    统一图架构:
    ┌─────────────────────────────────────────────────────────────────┐
    │                           START                                  │
    │                             │                                    │
    │                          router                                  │
    │                       ↙         ↘                                │
    │   ┌───────────────────────┐   ┌───────────────────────┐        │
    │   │    💬 Chat Mode       │   │   🔬 DeepSearch       │        │
    │   │                       │   │                       │        │
    │   │  rewrite              │   │  kb_precheck          │        │
    │   │     ↓                 │   │     ↓                 │        │
    │   │  context_retrieval    │   │  planning ◄────┐      │        │
    │   │  (history + kb)       │   │     ↓          │      │        │
    │   │     ↓                 │   │  search? ──────┘      │        │
    │   │  chatbot ◄────┐       │   │     ↓                 │        │
    │   │     ↓         │       │   │  summary              │        │
    │   │  tools? ──────┘       │   │     ↓                 │        │
    │   │     ↓                 │   │    END                │        │
    │   │    END                │   │                       │        │
    │   └───────────────────────┘   └───────────────────────┘        │
    └─────────────────────────────────────────────────────────────────┘

    Args:
        model: LLM 实例
        tools: 工具列表
        checkpointer: 可选的 checkpointer 用于状态持久化
        enable_rewrite: 是否启用代词消解节点

    Returns:
        编译后的 CompiledStateGraph
    """
    from app.core.settings import get_settings

    settings = get_settings()

    # 绑定工具到模型
    if tools:
        logger.info(f"🔧 Binding {len(tools)} tools to model: {[t.name for t in tools]}")
        model_with_tools = model.bind_tools(tools)
    else:
        logger.warning("⚠️ No tools provided to agent")
        model_with_tools = model

    # 创建节点
    tool_node = ToolNode(tools) if tools else None
    rewrite_node = create_rewrite_node(model) if enable_rewrite else None
    context_node = create_context_node(settings)
    chatbot_node = create_context_aware_chatbot_node(model_with_tools)
    kb_precheck_node = create_kb_precheck_node(settings)
    planning_node = create_planning_node(model, settings)
    search_node = create_search_node(settings)
    summary_node = create_summary_node(model)

    # 构建状态图
    workflow = StateGraph(AgentState)

    # ===== 添加所有节点 =====
    # 入口路由节点
    workflow.add_node("router", lambda state: state)  # 透传节点

    # 普通对话分支
    if rewrite_node:
        workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("context_retrieval", context_node)
    workflow.add_node("chatbot", chatbot_node)
    if tool_node:
        workflow.add_node("tools", tool_node)

    # DeepSearch 分支
    workflow.add_node("kb_precheck", kb_precheck_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("search", search_node)
    workflow.add_node("summary", summary_node)

    # ===== 入口路由 =====
    workflow.set_entry_point("router")
    workflow.add_conditional_edges(
        "router",
        mode_router,
        {
            "rewrite": "rewrite" if rewrite_node else "context_retrieval",
            "kb_precheck": "kb_precheck",
        },
    )

    # ===== 普通对话分支边 =====
    if rewrite_node:
        workflow.add_edge("rewrite", "context_retrieval")

    workflow.add_edge("context_retrieval", "chatbot")

    if tool_node:
        workflow.add_conditional_edges(
            "chatbot",
            tools_condition,
            {
                "tools": "tools",
                "__end__": END,
            },
        )
        workflow.add_edge("tools", "chatbot")
    else:
        workflow.add_edge("chatbot", END)

    # ===== DeepSearch 分支边 =====
    workflow.add_edge("kb_precheck", "planning")
    workflow.add_conditional_edges(
        "planning",
        planning_router,
        {
            "search": "search",
            "summary": "summary",
        },
    )
    workflow.add_edge("search", "planning")  # 循环回到 planning
    workflow.add_edge("summary", END)

    # 编译并返回
    return workflow.compile(checkpointer=checkpointer)


# ========== 5. 便捷工厂函数 ==========


def create_default_agent(
    model: ChatOpenAI,
    checkpointer=None,
    enable_rewrite: bool = True,
) -> StateGraph:
    """
    使用默认工具集创建 Agent。

    包含：
    - 时间/计算器工具
    - RAG 检索工具（历史对话检索）
    - Tavily 搜索工具（如果配置了 API Key）

    注意：知识库检索已集成到 context_retrieval 节点中，
    不再作为工具由模型自主调用，而是自动执行。
    """
    from app.core.settings import get_settings
    from app.tools import AVAILABLE_TOOLS
    from app.tools.rag_tool import rag_search
    from app.tools.tavily_tool import web_search

    settings = get_settings()

    # 基础工具
    all_tools = list(AVAILABLE_TOOLS)

    # 添加 RAG 工具（历史对话检索，作为备用工具）
    all_tools.append(rag_search)

    # 添加 Tavily 搜索工具
    if settings.tavily_api_key:
        all_tools.append(web_search)

    return create_agent_graph(
        model=model,
        tools=all_tools,
        checkpointer=checkpointer,
        enable_rewrite=enable_rewrite,
    )
