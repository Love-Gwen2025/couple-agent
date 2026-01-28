from sqlalchemy import BigInteger, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentWorkflow(Base):
    """
    AgentWorkflow 流程版本实体，对应 t_agent_workflow 表。

    说明：
    - append-only：更新流程时创建新版本，不覆盖旧版本
    - 属于某个 Agent（kind=single）
    - definition_json 保存 DAG 定义（含节点/边/位置与配置）
    """

    __tablename__ = "t_agent_workflow"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

