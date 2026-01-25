"""
数据转换器 - MapStruct 风格

统一 Model → VO 的转换逻辑，确保类型安全和一致性。
模型层的 to_vo() 方法保留用于简单场景，复杂场景使用转换器。

注意: VO 中的 ID 字段使用 SnowflakeId 类型，会自动序列化为字符串，
因此转换时可以直接传入原始值（int 或 str），无需手动调用 str()。
"""

from app.models.conversation import Conversation
from app.models.message import Message
from app.schema.conversation import ConversationVo, MessageVo


class ConversationConverter:
    """会话数据转换器"""

    @staticmethod
    def to_vo(model: Conversation) -> ConversationVo:
        """
        Conversation Model → ConversationVo

        SnowflakeId 类型会自动将 BigInt ID 序列化为字符串
        """
        return ConversationVo(
            id=model.id,  # SnowflakeId 自动序列化
            title=model.title,
            userId=model.user_id,  # SnowflakeId 自动序列化
            modelCode=model.model_code,
            agentId=model.agent_id,
            lastMessageId=model.last_message_id,  # SnowflakeId | None 自动处理
            lastMessageAt=model.last_message_at.isoformat() if model.last_message_at else None,
            avatar=model.avatar,
        )

    @staticmethod
    def to_vo_list(models: list[Conversation]) -> list[ConversationVo]:
        """批量转换"""
        return [ConversationConverter.to_vo(m) for m in models]

    @staticmethod
    def from_dict(data: dict) -> ConversationVo:
        """
        字典 → ConversationVo

        用于 Service 返回 dict 的场景
        """
        return ConversationVo(**data)


class MessageConverter:
    """消息数据转换器"""

    @staticmethod
    def to_vo(model: Message) -> MessageVo:
        """
        Message Model → MessageVo

        SnowflakeId 类型会自动将 BigInt ID 序列化为字符串
        """
        return MessageVo(
            id=model.id,  # SnowflakeId 自动序列化
            conversationId=model.conversation_id,  # SnowflakeId 自动序列化
            senderId=model.sender_id,  # SnowflakeId 自动序列化
            role=model.role,
            content=model.content or "",
            contentType=model.content_type or "TEXT",
            modelCode=model.model_code,
            tokenCount=model.token_count,
            createTime=model.create_time.isoformat() if model.create_time else None,
            parentId=model.parent_id,  # SnowflakeId | None 自动处理
            checkpointId=model.checkpoint_id,
        )

    @staticmethod
    def to_vo_list(models: list[Message]) -> list[MessageVo]:
        """批量转换"""
        return [MessageConverter.to_vo(m) for m in models]

    @staticmethod
    def from_dict(data: dict) -> MessageVo:
        """
        字典 → MessageVo

        用于 Service 返回 dict 的场景
        """
        return MessageVo(**data)
