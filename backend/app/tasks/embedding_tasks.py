"""
消息 Embedding Celery 任务

存储聊天消息的向量表示
"""

from loguru import logger

from app.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def store_message_embedding_task(
    self,
    db_url: str,
    message_id: int,
    conversation_id: int,
    user_id: int,
    role: str,
    content: str,
) -> dict:
    """
    Celery 任务：存储消息的 embedding 向量

    Args:
        db_url: 数据库连接 URL
        message_id: 消息 ID
        conversation_id: 会话 ID
        user_id: 用户 ID
        role: 角色 (user/assistant)
        content: 消息内容

    Returns:
        处理结果字典
    """
    import asyncio

    return asyncio.run(
        _store_embedding_async(db_url, message_id, conversation_id, user_id, role, content)
    )


async def _store_embedding_async(
    db_url: str,
    message_id: int,
    conversation_id: int,
    user_id: int,
    role: str,
    content: str,
) -> dict:
    """
    异步执行 embedding 存储
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.settings import get_settings
    from app.services.embedding_service import EmbeddingService
    from app.utils.content import extract_text_content

    settings = get_settings()

    # 创建数据库连接
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    result = {"message_id": message_id, "status": "failed"}

    # 提取纯文本内容
    content = extract_text_content(content)

    async with async_session() as db:
        embedding_service = EmbeddingService(settings)

        try:
            await embedding_service.store_message_embedding(
                db=db,
                message_id=message_id,
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
            )
            logger.info(f"Stored {role} embedding for message {message_id}")
            result["status"] = "done"

        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            raise  # 触发 Celery 重试

    await engine.dispose()
    return result
