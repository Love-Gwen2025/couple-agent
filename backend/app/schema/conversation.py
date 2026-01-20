"""
Pydantic Schema 定义

注意: 所有雪花 ID 使用 str 类型，避免 JavaScript 大整数精度丢失
"""

from pydantic import BaseModel, Field


class ConversationParam(BaseModel):
    """
    会话创建或修改参数。
    """

    id: str | None = Field(default=None, description="会话 ID，可为空")
    title: str | None = Field(default=None, description="会话标题")
    modelCode: str | None = Field(default=None, description="默认模型编码")


class MessageSendParam(BaseModel):
    """
    非流式消息发送参数。
    """

    conversationId: str = Field(..., description="会话 ID")
    content: str = Field(..., description="消息内容")
    contentType: str | None = Field(default="TEXT", description="消息类型")
    replyTo: str | None = Field(default=None, description="引用消息 ID")


class StreamChatParam(BaseModel):
    """
    流式对话请求参数。
    """

    conversationId: str = Field(..., description="会话 ID")
    content: str = Field(..., description="用户消息内容")
    modelCode: str | None = Field(default=None, description="模型编码（保留兼容）")
    modelId: str | None = Field(
        default=None, description="用户模型 ID，传此参数则使用用户自定义模型"
    )
    systemPrompt: str | None = Field(default=None, description="系统提示词")
    parentMessageId: str | None = Field(default=None, description="父消息 ID，用于构建消息树")
    regenerate: bool = Field(default=False, description="重新生成模式，从父消息分叉生成新回复")
    mode: str = Field(default="chat", description="对话模式: chat/deep_search")
    knowledgeBaseIds: list[int] | None = Field(
        default=None, description="启用的知识库 ID 列表，用于 RAG 检索"
    )


class MessageVo(BaseModel):
    """
    消息视图对象，用于统一返回消息。
    """

    id: str = Field(..., description="消息 ID")
    conversationId: str = Field(..., description="会话 ID")
    senderId: str = Field(..., description="发送者 ID")
    role: str = Field(..., description="角色 user/assistant")
    content: str = Field(..., description="消息内容")
    contentType: str = Field(default="TEXT", description="消息类型")
    modelCode: str | None = Field(default=None, description="模型编码")
    tokenCount: int | None = Field(default=None, description="Token 数")
    createTime: str | None = Field(default=None, description="创建时间 ISO8601")
    parentId: str | None = Field(default=None, description="父消息 ID，用于分支导航")
    checkpointId: str | None = Field(default=None, description="关联的 checkpoint ID")


class HistoryResponse(BaseModel):
    """消息历史响应，包含完整消息树"""

    messages: list[MessageVo] = Field(..., description="所有消息列表")
    currentMessageId: str | None = Field(default=None, description="当前选中的消息 ID")


class ConversationVo(BaseModel):
    """
    会话概要视图。
    """

    id: str = Field(..., description="会话 ID")
    title: str | None = Field(default=None, description="会话标题")
    userId: str = Field(..., description="拥有者 ID")
    modelCode: str | None = Field(default=None, description="默认模型编码")
    lastMessageId: str | None = Field(default=None, description="最后一条消息 ID")
    lastMessageAt: str | None = Field(default=None, description="最后消息时间 ISO8601")
    avatar: str | None = Field(default=None, description="会话头像")


class StreamChatEvent(BaseModel):
    """
    SSE 流式事件。
    """

    type: str = Field(..., description="事件类型：chunk/done/error")
    content: str | None = Field(default=None, description="内容片段")
    messageId: str | None = Field(default=None, description="消息 ID")
    conversationId: str | None = Field(default=None, description="会话 ID")
    error: str | None = Field(default=None, description="错误信息")
    tokenCount: int | None = Field(default=None, description="Token 使用量")
    checkpointId: str | None = Field(default=None, description="生成后的最新 checkpoint ID")
