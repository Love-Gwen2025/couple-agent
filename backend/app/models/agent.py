from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Agent(Base):
    """
    Agent 配置实体，对应 t_agent 表。

    Agent 是对外的执行单位：
    - kind=single: 单 Agent 执行
    - kind=team: 团队 Agent（Supervisor + workers）
    """

    __tablename__ = "t_agent"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="single")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    user_model_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    default_workflow_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def to_vo(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "kind": self.kind,
            "name": self.name,
            "description": self.description,
            "systemPrompt": self.system_prompt,
            "userModelId": self.user_model_id,
            "defaultWorkflowId": self.default_workflow_id,
            "status": self.status,
            "createTime": self.create_time.isoformat() if self.create_time else None,
            "updateTime": self.update_time.isoformat() if self.update_time else None,
        }
