"""
聊天相关 API 路由 - 使用 LangGraph 自动状态管理
"""

import json

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.dependencies.services import ChatServiceDep, ConversationServiceDep
from app.schema.base import ApiResult
from app.schema.conversation import StreamChatParam

router = APIRouter(prefix="/chat", tags=["聊天"])


# create_chat_service 已移动到 dependencies/services.py 作为依赖注入


@router.post("/stream")
async def stream_chat(
    payload: StreamChatParam,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    chat_service: ChatServiceDep = None,  # 依赖注入
    conv_service: ConversationServiceDep = None,  # 依赖注入
    current: CurrentUser = Depends(get_current_user),
):
    """
    流式对话：使用 LangGraph 自动管理对话历史，逐 token 输出。
    """
    try:
        await conv_service.ensure_owner(int(payload.conversationId), current.id)
    except PermissionError as ex:
        logger.warning(
            f"Permission denied: user={current.id}, conversation={payload.conversationId}"
        )
        response.status_code = status.HTTP_403_FORBIDDEN
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ApiResult.error("CONV-403", str(ex)).model_dump(),
        )

    async def event_generator():
        async for chunk in chat_service.stream(
            user_id=current.id,
            conversation_id=int(payload.conversationId),
            content=payload.content,
            model_code=payload.modelCode,
            model_id=payload.modelId,
            regenerate=payload.regenerate,
            parent_message_id=int(payload.parentMessageId) if payload.parentMessageId else None,
            db=db,
            mode=payload.mode,
            knowledge_base_ids=payload.knowledgeBaseIds,
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/send", response_model=ApiResult[str])
async def chat(
    payload: StreamChatParam,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    chat_service: ChatServiceDep = None,  # 依赖注入
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[str]:
    """
    同步对话（已废弃，请使用 /stream）。
    为保持兼容性，此接口收集流式结果后一次返回。
    """
    try:
        # 收集流式结果
        full_reply = []
        async for chunk in chat_service.stream(
            user_id=current.id,
            conversation_id=int(payload.conversationId),
            content=payload.content,
            model_code=payload.modelCode,
            model_id=payload.modelId,
            regenerate=payload.regenerate,
            parent_message_id=int(payload.parentMessageId) if payload.parentMessageId else None,
            db=db,
            mode=payload.mode,
            knowledge_base_ids=payload.knowledgeBaseIds,
        ):
            data = json.loads(chunk)
            if data.get("type") == "chunk":
                full_reply.append(data.get("content", ""))

        return ApiResult.ok("".join(full_reply))
    except PermissionError as ex:
        logger.warning(
            f"Permission denied: user={current.id}, conversation={payload.conversationId}"
        )
        response.status_code = status.HTTP_403_FORBIDDEN
        return ApiResult.error("CONV-403", str(ex))


@router.get("/health", response_model=ApiResult[str])
async def health() -> ApiResult[str]:
    """
    健康检查接口。
    """
    return ApiResult.ok("Chat service is healthy")
