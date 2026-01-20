"""
知识库 API 路由

提供知识库管理、文档上传、召回测试等接口。
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.settings import get_settings
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.base import ApiResult, PageParams, PageResponse
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_service import KnowledgeService
from app.tasks.document_tasks import process_document_task
from app.utils.alioss_util import get_oss_client

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


# ========== Schema 定义 ==========


class CreateKnowledgeBaseParam(BaseModel):
    """创建知识库参数"""

    name: str
    description: str | None = None


class KnowledgeBaseVo(BaseModel):
    """知识库视图"""

    id: str
    name: str
    description: str | None
    documentCount: int
    chunkCount: int
    createTime: str | None
    updateTime: str | None


class DocumentVo(BaseModel):
    """文档视图"""

    id: str
    fileName: str
    fileUrl: str
    fileSize: int | None
    fileType: str | None
    chunkCount: int
    status: str
    createTime: str | None


class RecallTestParam(BaseModel):
    """召回测试参数"""

    query: str
    mode: str = "union"  # union（并集）、intersection（交集）、vector（纯向量）
    topK: int = 5
    threshold: float = 0.5


class RecallResultVo(BaseModel):
    """召回结果"""

    content: str
    similarity: float
    fileName: str | None
    chunkIndex: int
    metadata: dict | None = None


# ========== 知识库 CRUD ==========


@router.post("", response_model=ApiResult[KnowledgeBaseVo])
async def create_knowledge_base(
    payload: CreateKnowledgeBaseParam,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[KnowledgeBaseVo]:
    """
    创建知识库
    """
    service = KnowledgeService(db)
    kb = await service.create_knowledge_base(
        user_id=current.id,
        name=payload.name,
        description=payload.description,
    )
    return ApiResult.ok(KnowledgeBaseVo(**kb.to_vo()))


@router.get("", response_model=ApiResult[PageResponse])
async def list_knowledge_bases(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[PageResponse]:
    """
    列出用户的所有知识库
    """
    service = KnowledgeService(db)

    params = PageParams(page=page, size=size)

    kbs, total = await service.list_knowledge_bases(current.id, params)
    return ApiResult.ok(
        PageResponse.of(
            records=[KnowledgeBaseVo(**kb.to_vo()) for kb in kbs],
            total=total,
            page=params.page,
            size=params.size,
        )
    )


@router.get("/{kb_id}", response_model=ApiResult[KnowledgeBaseVo])
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[KnowledgeBaseVo]:
    """
    获取知识库详情
    """
    service = KnowledgeService(db)
    kb = await service.get_knowledge_base(int(kb_id), current.id)
    if kb is None:
        return ApiResult.fail("知识库不存在")
    return ApiResult.ok(KnowledgeBaseVo(**kb.to_vo()))


@router.delete("/{kb_id}", response_model=ApiResult[None])
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[None]:
    """
    删除知识库（级联删除文档和分块）
    """
    service = KnowledgeService(db)
    success = await service.delete_knowledge_base(int(kb_id), current.id)
    if not success:
        return ApiResult.fail("知识库不存在或无权限")
    return ApiResult.ok()


# ========== 文档管理 ==========


@router.post("/{kb_id}/documents", response_model=ApiResult[DocumentVo])
async def upload_document(
    kb_id: str,
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[DocumentVo]:
    """
    上传文档到知识库

    支持的格式：PDF、Word (docx)、TXT
    文档会在后台异步处理（解析 → 分块 → 向量化）
    """
    settings = get_settings()
    kb_service = KnowledgeService(db)

    # 检查知识库是否存在
    kb = await kb_service.get_knowledge_base(int(kb_id), current.id)
    if kb is None:
        return ApiResult.fail("知识库不存在")

    # 验证文件类型
    file_name = file.filename or "unknown"
    file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if file_ext not in ["pdf", "docx", "doc", "txt"]:
        return ApiResult.fail(f"不支持的文件类型: {file_ext}")

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 上传到 OSS
    try:
        oss_key = f"knowledge/{current.id}/{kb_id}/{file_name}"
        oss_client = get_oss_client()
        result = await asyncio.to_thread(oss_client.upload_bytes, content, oss_key)
        if not result.get("success"):
            return ApiResult.error("OSS_ERROR", f"OSS 上传失败: {result.get('request_id')}")
        file_url = result["url"]
    except Exception as e:
        logger.error(f"OSS upload failed: {e}")
        return ApiResult.error("OSS_ERROR", f"文件上传失败: {e}")

    # 创建文档记录
    doc = await kb_service.create_document(
        knowledge_base_id=int(kb_id),
        file_name=file_name,
        file_url=file_url,
        file_size=file_size,
        file_type=file_ext,
    )

    # 启动 Celery 后台处理任务
    db_url = str(settings.database_url)
    process_document_task.delay(
        db_url,
        doc.id,
        int(kb_id),
        file_url,
        file_name,
        file_ext,
    )
    logger.info(f"Queued document processing task for doc_id={doc.id}")

    return ApiResult.ok(DocumentVo(**doc.to_vo()))


@router.get("/{kb_id}/documents", response_model=ApiResult[PageResponse])
async def list_documents(
    kb_id: str,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[PageResponse]:
    """
    列出知识库的所有文档（分页）
    """
    kb_service = KnowledgeService(db)

    # 检查知识库权限
    kb = await kb_service.get_knowledge_base(int(kb_id), current.id)
    if kb is None:
        return ApiResult.fail("知识库不存在")

    params = PageParams(page=page, size=size)
    docs, total = await kb_service.list_documents(int(kb_id), params)
    return ApiResult.ok(
        PageResponse.of(
            records=[DocumentVo(**doc.to_vo()) for doc in docs],
            total=total,
            page=params.page,
            size=params.size,
        )
    )


@router.delete("/{kb_id}/documents/{doc_id}", response_model=ApiResult[None])
async def delete_document(
    kb_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[None]:
    """
    删除文档（级联删除分块）
    """
    kb_service = KnowledgeService(db)

    # 检查知识库权限
    kb = await kb_service.get_knowledge_base(int(kb_id), current.id)
    if kb is None:
        return ApiResult.fail("知识库不存在")

    success = await kb_service.delete_document(int(doc_id))
    if not success:
        return ApiResult.fail("文档不存在")

    return ApiResult.ok()


# ========== 召回测试 ==========


@router.post("/{kb_id}/recall-test", response_model=ApiResult[list[RecallResultVo]])
async def recall_test(
    kb_id: str,
    payload: RecallTestParam,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[list[RecallResultVo]]:
    """
    召回测试

    支持三种检索模式：
    - vector: 纯向量检索
    - union: 混合检索（向量 + BM25 并集）
    - intersection: 混合检索（向量 + BM25 交集）
    """
    settings = get_settings()
    kb_service = KnowledgeService(db)
    embedding_service = EmbeddingService(settings)

    # 检查知识库权限
    kb = await kb_service.get_knowledge_base(int(kb_id), current.id)
    if kb is None:
        return ApiResult.fail("知识库不存在")

    # 执行检索
    if payload.mode == "vector":
        results = await embedding_service.search_knowledge_base(
            db=db,
            query=payload.query,
            knowledge_base_ids=[int(kb_id)],
            top_k=payload.topK,
            similarity_threshold=payload.threshold,
        )
    else:
        results = await embedding_service.hybrid_search_knowledge_base(
            db=db,
            query=payload.query,
            knowledge_base_ids=[int(kb_id)],
            top_k=payload.topK,
            similarity_threshold=payload.threshold,
            mode=payload.mode,
        )

    # 格式化结果
    recall_results = [
        RecallResultVo(
            content=r["content"],
            similarity=r.get("rrf_score", r.get("similarity", 0)),
            fileName=r.get("file_name"),
            chunkIndex=r.get("chunk_index", 0),
            metadata=r.get("metadata"),
        )
        for r in results
    ]

    return ApiResult.ok(recall_results)
