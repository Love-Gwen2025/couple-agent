"""
文档处理 Celery 任务

处理知识库文档的解析、分块、向量化
"""

from loguru import logger

from app.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_document_task(
    self,
    db_url: str,
    doc_id: int,
    kb_id: int,
    file_url: str,
    file_name: str,
    file_type: str,
) -> dict:
    """
    Celery 任务：处理文档（解析、分块、向量化）

    Args:
        db_url: 数据库连接 URL
        doc_id: 文档 ID
        kb_id: 知识库 ID
        file_url: 文件 URL（OSS）
        file_name: 文件名
        file_type: 文件类型

    Returns:
        处理结果字典
    """
    import asyncio

    # Celery 是同步的，需要运行异步函数
    return asyncio.run(
        _process_document_async(db_url, doc_id, kb_id, file_url, file_name, file_type)
    )


async def _process_document_async(
    db_url: str,
    doc_id: int,
    kb_id: int,
    file_url: str,
    file_name: str,
    file_type: str,
) -> dict:
    """
    异步执行文档处理

    为了复用现有的异步服务，在 Celery 任务中通过 asyncio.run 调用
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.settings import get_settings
    from app.services.document_parse_service import DocumentParseService
    from app.services.embedding_service import EmbeddingService
    from app.services.knowledge_service import KnowledgeService

    settings = get_settings()

    # 创建新的数据库连接（Celery Worker 独立进程，需要新连接）
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    result = {"doc_id": doc_id, "status": "failed", "chunk_count": 0}

    async with async_session() as db:
        kb_service = KnowledgeService(db)
        embedding_service = EmbeddingService(settings)
        parse_service = DocumentParseService(settings, embedding_service)

        try:
            # 更新状态为处理中
            await kb_service.update_document_status(doc_id, "processing")

            # 处理文档
            chunks = await parse_service.process_document(file_url, file_name, file_type)

            if chunks:
                # 存储分块
                await kb_service.create_chunks(kb_id, doc_id, chunks)

            # 更新状态为完成
            await kb_service.update_document_status(doc_id, "done", len(chunks))
            logger.info(f"Document {doc_id} processed: {len(chunks)} chunks")

            result["status"] = "done"
            result["chunk_count"] = len(chunks)

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            await kb_service.update_document_status(doc_id, "failed")
            raise  # 抛出异常触发 Celery 重试

    await engine.dispose()
    return result
