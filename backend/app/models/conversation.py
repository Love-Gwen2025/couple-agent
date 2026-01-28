from datetime import datetime

from sqlalchemy import JSON, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Conversation(Base):
    """
    1. 会话实体，对应 t_conversation 表。
    """

    __tablename__ = "t_conversation"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    model_code: Mapped[str | None] = mapped_column(String(50))
    agent_id: Mapped[int | None] = mapped_column(BigInteger)
    workflow_id: Mapped[int | None] = mapped_column(BigInteger)
    last_message_id: Mapped[int | None] = mapped_column(BigInteger)
    last_message_at: Mapped[datetime | None] = mapped_column()
    ext: Mapped[dict | None] = mapped_column(JSON)
    avatar: Mapped[str | None] = mapped_column(String(512))
    current_message_id: Mapped[int | None] = mapped_column(BigInteger)

    def to_vo(self) -> dict:
        """
        转为接口会话视图（简单场景备用）。

        注意: 推荐使用 ConversationConverter.to_vo()，
        它会配合 SnowflakeId 类型自动处理 BigInt 序列化。
        """
        return {
            "id": self.id,  # SnowflakeId 会自动序列化为字符串
            "title": self.title,
            "userId": self.user_id,  # SnowflakeId 会自动序列化为字符串
            "modelCode": self.model_code,
            "agentId": self.agent_id,
            "workflowId": self.workflow_id,
            "lastMessageId": self.last_message_id,  # SnowflakeId | None 自动处理
            "lastMessageAt": self.last_message_at.isoformat() if self.last_message_at else None,
            "avatar": self.avatar,
        }
