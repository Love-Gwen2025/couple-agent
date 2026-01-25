from sqlalchemy import BigInteger, Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class McpTool(Base):
    """
    MCP Tool 元数据表，对应 t_mcp_tool。
    """

    __tablename__ = "t_mcp_tool"

    server_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    input_schema: Mapped[dict | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def to_vo(self) -> dict:
        return {
            "id": self.id,
            "serverId": self.server_id,
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "enabled": self.enabled,
            "createTime": self.create_time.isoformat() if self.create_time else None,
            "updateTime": self.update_time.isoformat() if self.update_time else None,
        }

