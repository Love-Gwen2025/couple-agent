"""
Service 依赖注入

使用 FastAPI 的 Depends 机制提供 Service 实例，
避免每个路由方法内部手动创建 Service。
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.redis import get_redis
from app.core.settings import Settings, get_settings
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.utils.session_store import SessionStore

# ==================== 基础服务依赖 ====================


def get_conversation_service(
    db: AsyncSession = Depends(get_db_session),
) -> ConversationService:
    """
    获取 ConversationService 实例

    通过依赖注入获取数据库 session，避免手动传递
    """
    return ConversationService(db)


def get_auth_service(
    db: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """
    获取 AuthService 实例

    包含数据库、Redis 和配置的完整依赖链
    """
    store = SessionStore(redis, settings)
    return AuthService(db, store, settings)


# ==================== 复合服务依赖 ====================


def get_chat_service(
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    """
    获取 ChatService 实例

    不再使用内置模型，用户需在应用内自行配置模型
    """
    conv_service = ConversationService(db)

    # 可选服务 - 根据配置启用 Embedding
    embedding_service = None
    use_local_embedding = settings.ai_embedding_provider == "local"
    has_remote_key = settings.ai_embedding_api_key
    if use_local_embedding or has_remote_key:
        embedding_service = EmbeddingService(settings)

    return ChatService(
        conversation_service=conv_service,
        embedding_service=embedding_service,
        settings=settings,
    )


# ==================== 类型别名（方便路由使用） ====================

# 使用类型别名简化路由参数声明
ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
