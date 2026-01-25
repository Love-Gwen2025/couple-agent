from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentMember(Base):
    """
    Team Agent 成员绑定表，对应 t_agent_member。
    """

    __tablename__ = "t_agent_member"

    team_agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    member_agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def to_vo(self) -> dict:
        return {
            "id": self.id,
            "teamAgentId": self.team_agent_id,
            "memberAgentId": self.member_agent_id,
            "sortOrder": self.sort_order,
        }

