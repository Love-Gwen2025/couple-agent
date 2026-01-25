from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentKnowledgeBase(Base):
    """
    Agent-知识库绑定表，对应 t_agent_kb。
    """

    __tablename__ = "t_agent_kb"

    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    def to_vo(self) -> dict:
        return {
            "id": self.id,
            "agentId": self.agent_id,
            "knowledgeBaseId": self.knowledge_base_id,
        }

