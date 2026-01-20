from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.converter.converter import (
    ConversationConverter,
    MessageConverter,
)
from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.base import ApiResult, PageParams, PageResponse
from app.schema.conversation import (
    ConversationParam,
    ConversationVo,
    HistoryResponse,
    MessageSendParam,
    MessageVo,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversation", tags=["会话"])


@router.post("/create/assistant", response_model=ApiResult[ConversationVo])
async def create_assistant_conversation(
    payload: ConversationParam,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[ConversationVo]:
    """
    创建机器人会话，标题缺省时使用默认文案。
    """
    service = ConversationService(db)
    conv_id = await service.create_conversation(current.id, payload.title, payload.modelCode)
    conversation = await service.get_conversation(conv_id, current.id)
    return ApiResult.ok(ConversationConverter.to_vo(conversation))


@router.get("/list", response_model=ApiResult[PageResponse])
async def list_conversations(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[PageResponse]:
    """
    查询当前用户会话列表，支持分页。

    Args:
        page: 页码，从 1 开始
        size: 每页大小
    """
    # 构造分页参数
    params = PageParams(page=page, size=size)
    service = ConversationService(db)
    items, total = await service.list_conversations_page(current.id, params)
    return ApiResult.ok(
        PageResponse.of(
            records=[ConversationConverter.to_vo(item) for item in items],
            total=total,
            page=params.page,
            size=params.size,
        )
    )


@router.get("/history", response_model=ApiResult[HistoryResponse])
async def history(
    conversationId: str,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[HistoryResponse]:
    """
    查询会话历史消息（返回完整消息树）
    """
    conv_service = ConversationService(db)
    # ForbiddenError 由全局异常处理器捕获
    await conv_service.ensure_owner(int(conversationId), current.id)
    messages, current_message_id = await conv_service.history(current.id, int(conversationId))
    logger.info(f"[history] messages count: {len(messages)}")
    return ApiResult.ok(
        HistoryResponse(
            messages=[MessageConverter.to_vo(msg) for msg in messages],
            currentMessageId=str(current_message_id) if current_message_id else None,
        )
    )


@router.get("/{conversation_id}", response_model=ApiResult[ConversationVo])
async def get_conversation_detail(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[ConversationVo]:
    """
    获取会话详情，校验归属。
    """
    service = ConversationService(db)
    conversation = await service.get_conversation(int(conversation_id), current.id)
    return ApiResult.ok(ConversationConverter.to_vo(conversation))


@router.post("/send", response_model=ApiResult[MessageVo])
async def send_message(
    payload: MessageSendParam,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[MessageVo]:
    """
    同步消息发送并落库。
    """
    service = ConversationService(db)
    await service.ensure_owner(int(payload.conversationId), current.id)
    message = await service.persist_message(
        conversation_id=int(payload.conversationId),
        sender_id=current.id,
        role="user",
        content=payload.content,
        content_type=payload.contentType or "TEXT",
    )
    return ApiResult.ok(MessageConverter.to_vo(message))


# /history 路由已移到 /{conversation_id} 之前定义


@router.patch("/modify", response_model=ApiResult[None])
async def modify_conversation(
    payload: ConversationParam,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[None]:
    """
    修改会话标题。
    """
    service = ConversationService(db)
    await service.modify_conversation(
        current.id, int(payload.id) if payload.id else None, payload.title
    )
    return ApiResult.ok()


@router.delete("/{conversation_id}", response_model=ApiResult[None])
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[None]:
    """
    删除会话及其消息。
    """
    service = ConversationService(db)
    await service.delete_conversation(current.id, int(conversation_id))
    return ApiResult.ok()
