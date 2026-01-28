from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    """
    Workflow 执行状态（最小闭环）。

    注意：依赖（embedding_service/db_session/conversation_id）通过 LangGraph config 注入，
    避免 checkpoint 序列化问题。
    """

    messages: Annotated[list[AnyMessage], add_messages]
    mode: str
    knowledge_base_ids: list[int]
    history_context: str
    kb_context: str
    route: str | None

