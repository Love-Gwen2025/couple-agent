"""
聊天服务 v3 - 知识库集成架构

架构：
1. 只传 thread_id + checkpoint_id，LangGraph 自动管理历史
2. 知识库 RAG 自动集成到 context_retrieval 节点
3. DeepSearch 模式支持知识库预检查
4. 每轮结束持久化到数据库（用于展示和审计）
"""

import json
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import create_agent_graph, create_default_agent
from app.agent.platform_tools import build_tools_for_tool_refs
from app.core.checkpointer import create_checkpointer
from app.core.constants import AI_SENDER_ID, MAX_TITLE_LENGTH
from app.core.settings import Settings
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.langfuse_service import get_langfuse_service
from app.services.model_service import ModelService
from app.services.workflow_service import WorkflowService
from app.tasks.embedding_tasks import store_message_embedding_task
from app.utils.content import extract_text_content
from app.workflow.compiler import compile_validated_workflow
from app.workflow.definition import WorkflowDefinition
from app.workflow.validation import validate_workflow_definition

# 系统提示词
SYSTEM_PROMPT = """你是一个智能助手。

请根据用户的问题与系统提供的参考资料进行回答，保持回答简洁、准确、有帮助。
如果需要使用工具，请先调用工具再作答。"""

TEAM_WORKER_SUFFIX = """\n\n你处于一个多 Agent 协作系统中：你的输出将提供给上级 Agent 生成最终回复。\n要求：\n1) 只输出结论、关键事实与建议，不要输出推理过程。\n2) 如引用资料/工具结果，请指出来源（简短即可）。\n3) 输出尽量结构化（要点/步骤）。\n"""


class ChatService:
    """
    聊天服务 v3 - 知识库集成架构

    特性：
    1. checkpoint_id 分支：支持从历史任意点分叉
    2. 代词消解：RewriteNode 自动处理
    3. 知识库 RAG：context_retrieval 节点自动检索
    4. 工具自主调用：模型决定是否调用 RAG/搜索
    5. 流式输出：逐 token 推送
    """

    def __init__(
        self,
        conversation_service: ConversationService,
        embedding_service: EmbeddingService | None = None,
        settings: Settings | None = None,
    ):
        self.conversation_service = conversation_service
        self.embedding_service = embedding_service
        self.settings = settings

    async def _create_title(
        self,
        msg: str,
        user_id: int,
        model_id: str | None,
        db: AsyncSession | None,
    ) -> str:
        """
        根据消息内容自动生成会话标题

        使用用户配置的模型生成标题，如果没有模型则截断消息
        """
        # 尝试用用户模型生成标题
        model = await self._get_model_for_user(user_id, model_id, db)
        if model:
            try:
                from langchain_core.messages import HumanMessage as HM

                prompt = (
                    "根据传入的消息,生成一个5-10字左右的标题,"
                    "内容力求准确,简明,扼要。"
                    "只输出标题本身，不要加引号或其他内容。\n"
                    f"消息: {msg}\n标题:"
                )
                response = await model.ainvoke([HM(content=prompt)])
                title = extract_text_content(response.content)
                return title.strip()[:MAX_TITLE_LENGTH]
            except Exception as e:
                logger.warning(f"Failed to generate title with AI: {e}")

        return msg[:MAX_TITLE_LENGTH]

    async def _get_model_for_user(
        self,
        user_id: int,
        model_id: str | None,
        db: AsyncSession | None,
    ):
        """
        根据 model_id 获取用户配置的模型
        Returns:
            ChatModel 实例（LangChain 兼容），如果未找到则返回 None
        """
        from app.services.user_model_service import UserModelService

        # 没有传 model_id，直接返回 None
        if not model_id:
            logger.warning("No model_id provided, cannot proceed without user model")
            return None

        # 查询用户模型
        if db:
            user_model_service = UserModelService(db)
            target_model = await user_model_service.get_with_decrypted_key(user_id, int(model_id))

            if target_model:
                model_service = ModelService.from_user_model(target_model)
                logger.info(f"Using user model: {target_model.model_name} (id={model_id})")
                return model_service.get_model()

        logger.warning(f"User model {model_id} not found")
        return None

    def _build_langgraph_config(
        self,
        conversation_id: int,
        db: AsyncSession | None,
        checkpoint_id: str | None = None,
    ) -> dict:
        """
        构建 LangGraph 配置

        Args:
            conversation_id: 会话 ID
            db: 数据库会话（用于 RAG）
            checkpoint_id: 可选的 checkpoint ID（用于 regenerate 回退）

        Returns:
            LangGraph 配置字典
        """
        config = {
            "configurable": {
                "thread_id": str(conversation_id),
                "embedding_service": self.embedding_service,
                "db_session": db,
                "conversation_id": conversation_id,
            }
        }
        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id
        return config

    def _format_sse_event(self, event_type: str, conversation_id: int, **kwargs) -> str:
        """
        格式化 SSE 事件为 JSON

        Args:
            event_type: 事件类型 (chunk/tool_start/tool_end/done)
            conversation_id: 会话 ID
            **kwargs: 额外的事件数据

        Returns:
            JSON 格式的字符串
        """
        return json.dumps(
            {"type": event_type, "conversationId": str(conversation_id), **kwargs},
            ensure_ascii=False,
        )

    async def _bind_agent_to_conversation(self, conversation, agent_id: int | None) -> None:
        """绑定 Agent 到会话（会话以 agent 为执行单位，不允许覆盖）"""
        if agent_id is None:
            return

        if conversation.agent_id and conversation.agent_id != agent_id:
            raise ValueError("该会话已绑定其他 Agent，禁止覆盖")

        if conversation.agent_id is None:
            conversation.agent_id = agent_id
            await self.conversation_service.db.commit()

    async def _ensure_execution_spec(
        self,
        conversation,
        user_id: int,
        db: AsyncSession | None,
    ) -> dict | None:
        """
        确保会话已写入执行快照（ExecutionSpec）。

        - 仅对 kind=single Agent 生效
        - 一旦写入，后续会话执行必须使用该快照（避免 Agent 配置漂移）
        """
        ext = dict(conversation.ext or {})
        existing = ext.get("executionSpec")
        if existing:
            workflow_id = existing.get("workflowId")
            if workflow_id and conversation.workflow_id is None:
                conversation.workflow_id = int(workflow_id)
                await self.conversation_service.db.commit()
            if workflow_id and conversation.workflow_id and int(workflow_id) != int(conversation.workflow_id):
                raise ValueError("会话 workflow_id 与 executionSpec.workflowId 不一致")
            return existing

        if conversation.agent_id is None:
            return None

        if not db:
            raise ValueError("当前会话已绑定 Agent，但缺少数据库会话，无法执行。")

        agent_service = AgentService(db)
        agent = await agent_service.get_agent(user_id, int(conversation.agent_id))
        if not agent:
            raise ValueError("Agent 不存在或无权限")

        # team Agent 首期不写入 workflow 执行快照（后续做 B 时再扩展）
        if agent.kind != "single":
            return None

        workflow_service = WorkflowService(db)
        execution_spec = await workflow_service.build_execution_spec(user_id, int(conversation.agent_id))

        # 若会话已显式绑定 workflow_id，则以会话为准（保持回放一致性）
        if conversation.workflow_id:
            wf = await workflow_service.get_workflow(user_id, int(conversation.workflow_id))
            if not wf:
                raise ValueError("会话绑定的 workflow 不存在或无权限")
            execution_spec["workflowId"] = int(conversation.workflow_id)
            execution_spec["workflowSchemaVersion"] = int(wf.schema_version)

        ext["executionSpec"] = execution_spec
        conversation.ext = ext
        conversation.workflow_id = int(execution_spec["workflowId"])
        await self.conversation_service.db.commit()
        return execution_spec

    async def _generate_title_if_needed(
        self,
        conversation,
        content: str,
        user_id: int,
        agent_id: int | None,
        model_id: str | None,
        db: AsyncSession | None,
    ) -> str | None:
        """首次消息时生成会话标题"""
        if conversation.current_message_id:
            return None

        # 优先使用 Agent 绑定模型生成标题
        title_model_id = model_id
        execution_spec = (conversation.ext or {}).get("executionSpec")
        if not title_model_id and execution_spec and execution_spec.get("userModelId"):
            title_model_id = str(execution_spec.get("userModelId"))
        if not title_model_id and agent_id and db:
            agent_service = AgentService(db)
            agent = await agent_service.get_agent(user_id, agent_id)
            if agent:
                title_model_id = str(agent.user_model_id)

        generated_title = await self._create_title(content, user_id, title_model_id, db)
        await self.conversation_service.modify_conversation(
            user_id, conversation.id, generated_title
        )
        return generated_title

    async def _persist_user_message(
        self,
        conversation_id: int,
        user_id: int,
        content: str,
        model_code: str | None,
        parent_message_id: int | None,
        regenerate: bool,
    ):
        """持久化用户消息（regenerate 模式跳过）"""
        if regenerate:
            return None

        return await self.conversation_service.persist_message(
            conversation_id=conversation_id,
            sender_id=user_id,
            role="user",
            content=content,
            content_type="TEXT",
            model_code=model_code,
            parent_id=parent_message_id,
        )

    async def _get_parent_checkpoint(
        self, regenerate: bool, parent_message_id: int | None
    ) -> str | None:
        """获取 regenerate 回退的 checkpoint ID"""
        if not regenerate or not parent_message_id:
            return None

        parent_msg = await self.conversation_service.get_message_by_id(parent_message_id)
        if parent_msg and parent_msg.checkpoint_id:
            logger.info(f"[stream] Rollback to checkpoint: {parent_msg.checkpoint_id}")
            return parent_msg.checkpoint_id

        return None

    async def _prepare_stream_context(
        self,
        user_id: int,
        conversation_id: int,
        content: str,
        agent_id: int | None,
        model_code: str | None,
        model_id: str | None,
        regenerate: bool,
        parent_message_id: int | None,
        db: AsyncSession | None,
    ) -> tuple:
        """
        准备流式对话的上下文

        Returns:
            (conversation, generated_title, user_message, parent_checkpoint_id)
        """
        conversation = await self.conversation_service.ensure_owner(conversation_id, user_id)

        await self._bind_agent_to_conversation(conversation, agent_id)

        # 绑定后立即写入执行快照（single Agent），确保会话内配置不漂移
        await self._ensure_execution_spec(conversation, user_id, db)

        generated_title = await self._generate_title_if_needed(
            conversation, content, user_id, agent_id, model_id, db
        )

        user_message = await self._persist_user_message(
            conversation_id, user_id, content, model_code, parent_message_id, regenerate
        )

        parent_checkpoint_id = await self._get_parent_checkpoint(regenerate, parent_message_id)

        return conversation, generated_title, user_message, parent_checkpoint_id

    async def stream(
        self,
        user_id: int,
        conversation_id: int,
        content: str,
        agent_id: int | None = None,
        model_code: str | None = None,
        model_id: str | None = None,
        regenerate: bool = False,
        parent_message_id: int | None = None,
        db: AsyncSession | None = None,
        mode: str = "chat",
        knowledge_base_ids: list[int] | None = None,
    ) -> AsyncIterator[str]:
        """
        流式对话 - 使用 LangGraph 原生状态管理

        流程：
        1. 校验会话归属
        1.1 如果是首次发送消息，自动生成标题
        2. 持久化用户消息（regenerate 模式下跳过）
        3. 设置 RAG 上下文
        4. 调用 LangGraph（自动加载历史、执行工具、检索知识库）
        5. 流式输出
        6. 持久化助手回复

        Args:
            user_id: 用户 ID
            conversation_id: 会话 ID
            content: 用户消息内容
            agent_id: Agent ID（平台化后使用；会话绑定后不可覆盖）
            model_code: 模型编码（保留兼容）
            model_id: 用户模型 ID，传此参数则使用用户自定义模型
            regenerate: 重新生成模式，跳过用户消息持久化
            parent_message_id: 父消息 ID，用于构建消息树
            db: 数据库会话（用于 RAG）
            mode: 对话模式 ("chat" | "deep_search")
            knowledge_base_ids: 启用的知识库 ID 列表

        Yields:
            JSON 格式的 SSE 数据
        """
        # 1. 准备上下文（校验归属、生成标题、持久化用户消息、处理 regenerate）
        try:
            (
                conversation,
                generated_title,
                user_message,
                parent_checkpoint_id,
            ) = await self._prepare_stream_context(
                user_id,
                conversation_id,
                content,
                agent_id,
                model_code,
                model_id,
                regenerate,
                parent_message_id,
                db,
            )
        except ValueError as exc:
            yield self._format_sse_event("error", conversation_id, error=str(exc))
            return

        full_reply = []
        placeholder_message_id = -1

        # 2. 构建 LangGraph config
        config = self._build_langgraph_config(conversation_id, db, parent_checkpoint_id)

        logger.info(
            f"[stream] regenerate={regenerate}, parent_checkpoint_id={parent_checkpoint_id}"
        )

        # 用于在 checkpointer 上下文外访问的变量
        latest_checkpoint_id = None

        effective_agent_id = conversation.agent_id

        if effective_agent_id and not db:
            fallback = "当前会话已绑定 Agent，但缺少数据库会话，无法执行。"
            full_reply.append(fallback)
            yield self._format_sse_event(
                "chunk", conversation_id, content=fallback, messageId=placeholder_message_id
            )

        elif effective_agent_id:
            agent_service = AgentService(db)
            try:
                agent_cfg = await agent_service.get_agent_config(user_id, int(effective_agent_id))
            except Exception as exc:
                fallback = f"读取 Agent 配置失败: {exc}"
                full_reply.append(fallback)
                yield self._format_sse_event(
                    "chunk", conversation_id, content=fallback, messageId=placeholder_message_id
                )
                agent_cfg = None

            if agent_cfg:
                agent = agent_cfg["agent"]
                if agent.status != 1:
                    fallback = "该 Agent 已禁用，无法执行。"
                    full_reply.append(fallback)
                    yield self._format_sse_event(
                        "chunk", conversation_id, content=fallback, messageId=placeholder_message_id
                    )
                else:
                    # ========== 单 Agent ==========
                    if agent.kind == "single":
                        execution_spec = (conversation.ext or {}).get("executionSpec") or {}
                        if not execution_spec:
                            fallback = "该会话缺少可执行的 workflow 执行快照，无法执行。"
                            full_reply.append(fallback)
                            yield self._format_sse_event(
                                "chunk",
                                conversation_id,
                                content=fallback,
                                messageId=placeholder_message_id,
                            )
                        else:
                            tool_refs = list(execution_spec.get("toolRefs") or [])
                            kb_ids = [int(x) for x in (execution_spec.get("knowledgeBaseIds") or [])]
                            workflow_id = execution_spec.get("workflowId")

                            tools, tool_meta = await build_tools_for_tool_refs(db, user_id, tool_refs)
                            model = await self._get_model_for_user(
                                user_id, str(execution_spec.get("userModelId")), db
                            )

                            if not model:
                                fallback = "Agent 绑定的模型不可用，请检查模型配置。"
                                full_reply.append(fallback)
                                yield self._format_sse_event(
                                    "chunk",
                                    conversation_id,
                                    content=fallback,
                                    messageId=placeholder_message_id,
                                )
                            elif not workflow_id:
                                fallback = "会话未绑定 workflowId，无法执行。"
                                full_reply.append(fallback)
                                yield self._format_sse_event(
                                    "chunk",
                                    conversation_id,
                                    content=fallback,
                                    messageId=placeholder_message_id,
                                )
                            else:
                                workflow_service = WorkflowService(db)
                                wf = await workflow_service.get_workflow(user_id, int(workflow_id))
                                if not wf:
                                    fallback = "会话绑定的 workflow 不存在或无权限，无法执行。"
                                    full_reply.append(fallback)
                                    yield self._format_sse_event(
                                        "chunk",
                                        conversation_id,
                                        content=fallback,
                                        messageId=placeholder_message_id,
                                    )
                                else:
                                    definition = WorkflowDefinition(**(wf.definition_json or {}))
                                    validated = validate_workflow_definition(definition)

                                    async with create_checkpointer(self.settings) as checkpointer:
                                        graph, output_node_id = compile_validated_workflow(
                                            validated,
                                            model=model,
                                            tools=tools,
                                            checkpointer=checkpointer,
                                            settings=self.settings,
                                        )

                                        if regenerate and parent_checkpoint_id:
                                            input_messages = []
                                        else:
                                            input_messages = [
                                                SystemMessage(
                                                    content=execution_spec.get("systemPrompt")
                                                    or SYSTEM_PROMPT,
                                                    id="sys_instruction",
                                                ),
                                                HumanMessage(content=content),
                                            ]

                                        graph_input = {
                                            "messages": input_messages,
                                            "mode": mode,
                                            "knowledge_base_ids": kb_ids,
                                            "history_context": "",
                                            "kb_context": "",
                                            "route": None,
                                        }

                                        yield self._format_sse_event(
                                            "agent_start",
                                            conversation_id,
                                            agentId=str(execution_spec.get("agentId") or agent.id),
                                            agentName=str(
                                                execution_spec.get("agentName") or agent.name
                                            ),
                                            agentKind=str(
                                                execution_spec.get("agentKind") or agent.kind
                                            ),
                                            role="single",
                                        )

                                        langfuse_service = get_langfuse_service(self.settings)
                                        langfuse_handler = (
                                            langfuse_service.get_callback_handler(
                                                user_id=str(user_id) if user_id else None,
                                                session_id=str(conversation_id),
                                                trace_name=f"{mode}_agent",
                                                metadata={
                                                    "mode": mode,
                                                    "regenerate": regenerate,
                                                    "agentId": str(agent.id),
                                                    "workflowId": str(workflow_id),
                                                },
                                            )
                                            if langfuse_service
                                            else None
                                        )
                                        if langfuse_handler:
                                            config["callbacks"] = [langfuse_handler]

                                        async for event in graph.astream_events(
                                            graph_input, config=config, version="v2"
                                        ):
                                            kind = event.get("event", "")

                                            if kind == "on_chat_model_stream":
                                                metadata = event.get("metadata", {})
                                                node_name = metadata.get("langgraph_node", "")
                                                if node_name and node_name != output_node_id:
                                                    continue

                                                chunk = event.get("data", {}).get("chunk")
                                                if (
                                                    chunk
                                                    and hasattr(chunk, "content")
                                                    and chunk.content
                                                ):
                                                    token = extract_text_content(chunk.content)
                                                    if token:
                                                        full_reply.append(token)
                                                        yield self._format_sse_event(
                                                            "chunk",
                                                            conversation_id,
                                                            content=token,
                                                            messageId=placeholder_message_id,
                                                        )

                                            elif kind == "on_tool_start":
                                                tool_name = event.get("name", "unknown")
                                                meta = tool_meta.get(tool_name, {})
                                                yield self._format_sse_event(
                                                    "tool_start",
                                                    conversation_id,
                                                    tool=tool_name,
                                                    toolRef=meta.get("toolRef"),
                                                    toolDisplayName=meta.get("displayName"),
                                                    agentId=str(agent.id),
                                                    agentName=agent.name,
                                                )

                                            elif kind == "on_tool_end":
                                                tool_name = event.get("name", "unknown")
                                                meta = tool_meta.get(tool_name, {})
                                                yield self._format_sse_event(
                                                    "tool_end",
                                                    conversation_id,
                                                    tool=tool_name,
                                                    toolRef=meta.get("toolRef"),
                                                    toolDisplayName=meta.get("displayName"),
                                                    agentId=str(agent.id),
                                                    agentName=agent.name,
                                                )

                                        yield self._format_sse_event(
                                            "agent_end",
                                            conversation_id,
                                            agentId=str(execution_spec.get("agentId") or agent.id),
                                            agentName=str(
                                                execution_spec.get("agentName") or agent.name
                                            ),
                                            agentKind=str(
                                                execution_spec.get("agentKind") or agent.kind
                                            ),
                                            role="single",
                                            status="success",
                                        )

                                        # 获取最新 checkpoint
                                        config_for_list = {
                                            "configurable": {"thread_id": str(conversation_id)}
                                        }
                                        try:
                                            async for checkpoint_tuple in checkpointer.alist(
                                                config_for_list, limit=1
                                            ):
                                                checkpoint = checkpoint_tuple.checkpoint or {}
                                                latest_checkpoint_id = checkpoint.get("id")
                                                break
                                        except Exception as exc:
                                            logger.error(
                                                f"Failed to fetch latest checkpoint: {exc}"
                                            )

                    # ========== Team Agent ==========
                    else:
                        # 1) 拉取成员 agents
                        member_ids = agent_cfg.get("memberAgentIds") or []
                        worker_notes: list[dict[str, str]] = []

                        # 1.1 依次执行 workers（不持久化到会话 checkpoint）
                        for member_id in member_ids:
                            worker_cfg = await agent_service.get_agent_config(
                                user_id, int(member_id)
                            )
                            worker_agent = worker_cfg["agent"]

                            if worker_agent.status != 1:
                                continue

                            worker_tools, worker_tool_meta = await build_tools_for_tool_refs(
                                db, user_id, worker_cfg["toolRefs"]
                            )
                            worker_model = await self._get_model_for_user(
                                user_id, str(worker_agent.user_model_id), db
                            )
                            if not worker_model:
                                continue

                            worker_graph = create_agent_graph(
                                model=worker_model,
                                tools=worker_tools,
                                checkpointer=None,
                                enable_rewrite=True,
                            )

                            yield self._format_sse_event(
                                "agent_start",
                                conversation_id,
                                agentId=str(worker_agent.id),
                                agentName=worker_agent.name,
                                agentKind=worker_agent.kind,
                                role="worker",
                                parentAgentId=str(agent.id),
                            )

                            worker_input_messages = [
                                SystemMessage(
                                    content=(worker_agent.system_prompt or SYSTEM_PROMPT)
                                    + TEAM_WORKER_SUFFIX,
                                    id="sys_instruction",
                                ),
                                HumanMessage(content=content),
                            ]
                            worker_graph_input = {
                                "messages": worker_input_messages,
                                "mode": "chat",  # workers 统一使用 chat（减少重复 deep_search 开销）
                                "question": content,
                                "search_queries": [],
                                "references": {},
                                "planning_rounds": 0,
                                "knowledge_base_ids": worker_cfg["knowledgeBaseIds"] or [],
                                "history_context": "",
                                "kb_context": "",
                            }

                            # workers 的 token 不作为最终 chunk 输出，仅收集为过程信息
                            worker_text_parts: list[str] = []
                            async for event in worker_graph.astream_events(
                                worker_graph_input, config=config, version="v2"
                            ):
                                kind = event.get("event", "")

                                if kind == "on_chat_model_stream":
                                    metadata = event.get("metadata", {})
                                    node_name = metadata.get("langgraph_node", "")
                                    output_nodes = {"chatbot", "summary"}
                                    if node_name and node_name not in output_nodes:
                                        continue

                                    chunk = event.get("data", {}).get("chunk")
                                    if chunk and hasattr(chunk, "content") and chunk.content:
                                        token = extract_text_content(chunk.content)
                                        if token:
                                            worker_text_parts.append(token)

                                elif kind == "on_tool_start":
                                    tool_name = event.get("name", "unknown")
                                    meta = worker_tool_meta.get(tool_name, {})
                                    yield self._format_sse_event(
                                        "tool_start",
                                        conversation_id,
                                        tool=tool_name,
                                        toolRef=meta.get("toolRef"),
                                        toolDisplayName=meta.get("displayName"),
                                        agentId=str(worker_agent.id),
                                        agentName=worker_agent.name,
                                    )

                                elif kind == "on_tool_end":
                                    tool_name = event.get("name", "unknown")
                                    meta = worker_tool_meta.get(tool_name, {})
                                    yield self._format_sse_event(
                                        "tool_end",
                                        conversation_id,
                                        tool=tool_name,
                                        toolRef=meta.get("toolRef"),
                                        toolDisplayName=meta.get("displayName"),
                                        agentId=str(worker_agent.id),
                                        agentName=worker_agent.name,
                                    )

                            worker_text = "".join(worker_text_parts).strip()
                            if worker_text:
                                yield self._format_sse_event(
                                    "agent_output",
                                    conversation_id,
                                    agentId=str(worker_agent.id),
                                    agentName=worker_agent.name,
                                    role="worker",
                                    content=worker_text,
                                )
                                worker_notes.append(
                                    {
                                        "agentName": worker_agent.name,
                                        "content": worker_text,
                                    }
                                )

                            yield self._format_sse_event(
                                "agent_end",
                                conversation_id,
                                agentId=str(worker_agent.id),
                                agentName=worker_agent.name,
                                agentKind=worker_agent.kind,
                                role="worker",
                                status="success",
                            )

                        # 2) 执行 supervisor（持久化 checkpoint + 最终输出）
                        supervisor_tools, supervisor_tool_meta = await build_tools_for_tool_refs(
                            db, user_id, agent_cfg["toolRefs"]
                        )
                        supervisor_model = await self._get_model_for_user(
                            user_id, str(agent.user_model_id), db
                        )

                        if not supervisor_model:
                            fallback = "Team Agent 绑定的模型不可用，请检查模型配置。"
                            full_reply.append(fallback)
                            yield self._format_sse_event(
                                "chunk",
                                conversation_id,
                                content=fallback,
                                messageId=placeholder_message_id,
                            )
                        else:
                            async with create_checkpointer(self.settings) as checkpointer:
                                supervisor_graph = create_agent_graph(
                                    model=supervisor_model,
                                    tools=supervisor_tools,
                                    checkpointer=checkpointer,
                                    enable_rewrite=True,
                                )

                                team_context = ""
                                if worker_notes:
                                    team_context = "\n\n".join(
                                        [
                                            f"[{n['agentName']}]\n{n['content']}"
                                            for n in worker_notes
                                        ]
                                    )

                                if regenerate and parent_checkpoint_id:
                                    input_messages = []
                                else:
                                    input_messages = [
                                        SystemMessage(
                                            content=agent.system_prompt or SYSTEM_PROMPT,
                                            id="sys_instruction",
                                        ),
                                    ]
                                    if team_context:
                                        input_messages.append(
                                            SystemMessage(
                                                content="以下是多个专家 Agent 的中间结论（可引用用于综合，但不要原样照搬）：\n\n"
                                                + team_context,
                                                id="sys_team_context",
                                            )
                                        )
                                    input_messages.append(HumanMessage(content=content))

                                graph_input = {
                                    "messages": input_messages,
                                    "mode": mode,
                                    "question": content,
                                    "search_queries": [],
                                    "references": {
                                        "Agent协作": [team_context] if team_context else []
                                    },
                                    "planning_rounds": 0,
                                    "knowledge_base_ids": agent_cfg["knowledgeBaseIds"] or [],
                                    "history_context": "",
                                    "kb_context": "",
                                }

                                yield self._format_sse_event(
                                    "agent_start",
                                    conversation_id,
                                    agentId=str(agent.id),
                                    agentName=agent.name,
                                    agentKind=agent.kind,
                                    role="supervisor",
                                )

                                langfuse_service = get_langfuse_service(self.settings)
                                langfuse_handler = langfuse_service.get_callback_handler(
                                    user_id=str(user_id) if user_id else None,
                                    session_id=str(conversation_id),
                                    trace_name=f"{mode}_team_agent",
                                    metadata={
                                        "mode": mode,
                                        "regenerate": regenerate,
                                        "agentId": str(agent.id),
                                    },
                                )
                                if langfuse_handler:
                                    config["callbacks"] = [langfuse_handler]

                                async for event in supervisor_graph.astream_events(
                                    graph_input, config=config, version="v2"
                                ):
                                    kind = event.get("event", "")

                                    if kind == "on_chat_model_stream":
                                        metadata = event.get("metadata", {})
                                        node_name = metadata.get("langgraph_node", "")
                                        output_nodes = {"chatbot", "summary"}
                                        if node_name and node_name not in output_nodes:
                                            continue

                                        chunk = event.get("data", {}).get("chunk")
                                        if chunk and hasattr(chunk, "content") and chunk.content:
                                            token = extract_text_content(chunk.content)
                                            if token:
                                                full_reply.append(token)
                                                yield self._format_sse_event(
                                                    "chunk",
                                                    conversation_id,
                                                    content=token,
                                                    messageId=placeholder_message_id,
                                                )

                                    elif kind == "on_tool_start":
                                        tool_name = event.get("name", "unknown")
                                        meta = supervisor_tool_meta.get(tool_name, {})
                                        yield self._format_sse_event(
                                            "tool_start",
                                            conversation_id,
                                            tool=tool_name,
                                            toolRef=meta.get("toolRef"),
                                            toolDisplayName=meta.get("displayName"),
                                            agentId=str(agent.id),
                                            agentName=agent.name,
                                        )

                                    elif kind == "on_tool_end":
                                        tool_name = event.get("name", "unknown")
                                        meta = supervisor_tool_meta.get(tool_name, {})
                                        yield self._format_sse_event(
                                            "tool_end",
                                            conversation_id,
                                            tool=tool_name,
                                            toolRef=meta.get("toolRef"),
                                            toolDisplayName=meta.get("displayName"),
                                            agentId=str(agent.id),
                                            agentName=agent.name,
                                        )

                                yield self._format_sse_event(
                                    "agent_end",
                                    conversation_id,
                                    agentId=str(agent.id),
                                    agentName=agent.name,
                                    agentKind=agent.kind,
                                    role="supervisor",
                                    status="success",
                                )

                                config_for_list = {
                                    "configurable": {"thread_id": str(conversation_id)}
                                }
                                try:
                                    async for checkpoint_tuple in checkpointer.alist(
                                        config_for_list, limit=1
                                    ):
                                        checkpoint = checkpoint_tuple.checkpoint or {}
                                        latest_checkpoint_id = checkpoint.get("id")
                                        break
                                except Exception as exc:
                                    logger.error(f"Failed to fetch latest checkpoint: {exc}")

        else:
            # 兼容旧路径：动态获取模型（来自请求），使用默认 Agent 图
            model = await self._get_model_for_user(user_id, model_id, db)

            if model:
                async with create_checkpointer(self.settings) as checkpointer:
                    graph = create_default_agent(
                        model=model,
                        checkpointer=checkpointer,
                        enable_rewrite=True,
                    )

                    if regenerate and parent_checkpoint_id:
                        input_messages = []
                    else:
                        input_messages = [
                            SystemMessage(content=SYSTEM_PROMPT, id="sys_instruction"),
                            HumanMessage(content=content),
                        ]

                    graph_input = {
                        "messages": input_messages,
                        "mode": mode,
                        "question": content,
                        "search_queries": [],
                        "references": {},
                        "planning_rounds": 0,
                        "knowledge_base_ids": knowledge_base_ids or [],
                        "history_context": "",
                        "kb_context": "",
                    }

                    langfuse_service = get_langfuse_service(self.settings)
                    langfuse_handler = langfuse_service.get_callback_handler(
                        user_id=str(user_id) if user_id else None,
                        session_id=str(conversation_id),
                        trace_name=f"{mode}_chat",
                        metadata={"mode": mode, "regenerate": regenerate},
                    )
                    if langfuse_handler:
                        config["callbacks"] = [langfuse_handler]

                    async for event in graph.astream_events(
                        graph_input, config=config, version="v2"
                    ):
                        kind = event.get("event", "")

                        if kind == "on_chat_model_stream":
                            metadata = event.get("metadata", {})
                            node_name = metadata.get("langgraph_node", "")
                            output_nodes = {"chatbot", "summary"}
                            if node_name and node_name not in output_nodes:
                                continue

                            chunk = event.get("data", {}).get("chunk")
                            if chunk and hasattr(chunk, "content") and chunk.content:
                                token = extract_text_content(chunk.content)
                                if token:
                                    full_reply.append(token)
                                    yield self._format_sse_event(
                                        "chunk",
                                        conversation_id,
                                        content=token,
                                        messageId=placeholder_message_id,
                                    )

                        elif kind == "on_tool_start":
                            tool_name = event.get("name", "unknown")
                            yield self._format_sse_event(
                                "tool_start", conversation_id, tool=tool_name
                            )

                        elif kind == "on_tool_end":
                            tool_name = event.get("name", "unknown")
                            yield self._format_sse_event(
                                "tool_end", conversation_id, tool=tool_name
                            )

                    config_for_list = {"configurable": {"thread_id": str(conversation_id)}}
                    try:
                        async for checkpoint_tuple in checkpointer.alist(config_for_list, limit=1):
                            checkpoint = checkpoint_tuple.checkpoint or {}
                            latest_checkpoint_id = checkpoint.get("id")
                            break
                    except Exception as exc:
                        logger.error(f"Failed to fetch latest checkpoint: {exc}")

            else:
                fallback = f"暂未接入模型，回显: {content}"
                full_reply.append(fallback)
                yield self._format_sse_event(
                    "chunk", conversation_id, content=fallback, messageId=placeholder_message_id
                )

        # 5. 持久化助手消息
        reply_text = "".join(full_reply) if full_reply else ""

        # latest_checkpoint_id 已在上面的 checkpointer 上下文中获取

        # AI 消息的 parent_id 是用户消息的 ID
        ai_parent_id = user_message.id if user_message else parent_message_id

        assistant_message = await self.conversation_service.persist_message(
            conversation_id=conversation_id,
            sender_id=AI_SENDER_ID,
            role="assistant",
            content=reply_text,
            content_type="TEXT",
            model_code=model_code,
            token_count=len(reply_text),
            parent_id=ai_parent_id,
            checkpoint_id=latest_checkpoint_id,
        )

        # 6. 使用 Celery 异步存储 embedding（完全解耦，不阻塞响应）
        if self.embedding_service and self.settings:
            db_url = str(self.settings.database_url)
            if user_message:
                # 正常模式：存储用户消息
                store_message_embedding_task.delay(
                    db_url, user_message.id, conversation_id, user_id, "user", content
                )
            # 存储 AI 回复
            store_message_embedding_task.delay(
                db_url, assistant_message.id, conversation_id, user_id, "assistant", reply_text
            )
            logger.debug(f"Queued embedding tasks for conversation {conversation_id}")

        # 7. 发送完成信号
        # 获取用户消息 ID（regenerate 时使用 parent_message_id）
        user_message_id = user_message.id if user_message else parent_message_id

        yield json.dumps(
            {
                "type": "done",
                "messageId": str(assistant_message.id),
                "conversationId": str(conversation_id),
                "tokenCount": len(reply_text),
                "parentId": str(ai_parent_id) if ai_parent_id else None,
                "userMessageId": str(user_message_id) if user_message_id else None,
                "title": generated_title,  # 新生成的标题（如果有）
            },
            ensure_ascii=False,
        )

    async def _get_latest_checkpoint_id(
        self,
        conversation_id: int,
    ) -> str | None:
        """
        获取最新 checkpointId，用于在 SSE done 事件中返回。
        """
        try:
            # 复用仅包含 thread_id 的配置，确保读取最新状态
            config = {"configurable": {"thread_id": str(conversation_id)}}
            async with create_checkpointer(self.settings) as checkpointer:
                # 使用 alist 获取最新 checkpoint，以便获取 parent_config
                async for checkpoint_tuple in checkpointer.alist(config, limit=1):
                    # CheckpointTuple 是对象，使用属性访问
                    checkpoint = checkpoint_tuple.checkpoint or {}
                    parent_config = checkpoint_tuple.parent_config or {}

                    checkpoint_id = checkpoint.get("id")
                    parent_id = None
                    if parent_config:
                        configurable = parent_config.get("configurable", {}) or {}
                        parent_id = configurable.get("checkpoint_id")

                    return checkpoint_id, parent_id
                return None, None
        except Exception as exc:
            logger.error(f"Failed to fetch latest checkpoint info: {exc}")
            return None, None
