from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentTool(Base):
    """
    Agent-Tool 绑定表，对应 t_agent_tool。

    tool_ref 采用统一命名空间：
    - builtin:<tool_name>
    - mcp:<mcp_tool_id>
    """

    __tablename__ = "t_agent_tool"

    agent_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tool_ref: Mapped[str] = mapped_column(String(200), nullable=False)

    def to_vo(self) -> dict:
        return {
            "id": self.id,
            "agentId": self.agent_id,
            "toolRef": self.tool_ref,
        }

