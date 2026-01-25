from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class McpServer(Base):
    """
    MCP Server 配置表，对应 t_mcp_server。

    仅支持远程 HTTP(S) 连接。
    """

    __tablename__ = "t_mcp_server"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    headers_encrypted: Mapped[str | None] = mapped_column(Text)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def to_vo(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "name": self.name,
            "url": self.url,
            "status": self.status,
            "createTime": self.create_time.isoformat() if self.create_time else None,
            "updateTime": self.update_time.isoformat() if self.update_time else None,
        }

