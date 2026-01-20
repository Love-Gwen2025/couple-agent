"""
知识库服务

提供知识库的 CRUD 操作、文档管理和召回测试功能。
"""

from typing import Any

from loguru import logger
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.schema.base import PageParams
from app.utils.snowflake import generate_id


class KnowledgeService:
    """
    知识库服务

    功能：
    1. 知识库 CRUD（创建、列表、删除）
    2. 文档管理（上传、列表、删除）
    3. 召回测试（语义检索 + BM25 混合检索）
    """

    def __init__(self, db: AsyncSession):
        """
        初始化知识库服务

        Args:
            db: 数据库会话
        """
        self.db = db

    # ========== 知识库 CRUD ==========

    async def create_knowledge_base(
        self,
        user_id: int,
        name: str,
        description: str | None = None,
    ) -> KnowledgeBase:
        """
        创建知识库

        Args:
            user_id: 用户 ID
            name: 知识库名称
            description: 知识库描述

        Returns:
            创建的知识库实体
        """
        kb = KnowledgeBase(
            id=generate_id(),
            user_id=user_id,
            name=name,
            description=description,
        )
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        logger.info(f"Created knowledge base: {kb.id} - {name}")
        return kb

    async def list_knowledge_bases(
        self, user_id: int, page_params: PageParams
    ) -> tuple[list[KnowledgeBase], int]:
        """
        列出用户的所有知识库

        Args:
            user_id: 用户 ID

        Returns:
            知识库列表
        """
        # 1.查询总数
        count_result = await self.db.execute(
            select(func.count()).select_from(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # 查询当页数据
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.user_id == user_id)
            .order_by(KnowledgeBase.update_time.desc())
            .limit(page_params.size)
            .offset(page_params.offset)
        )
        return list(result.scalars().all()), total

    async def get_knowledge_base(
        self,
        kb_id: int,
        user_id: int | None = None,
    ) -> KnowledgeBase | None:
        """
        获取知识库详情

        Args:
            kb_id: 知识库 ID
            user_id: 可选的用户 ID（用于权限校验）

        Returns:
            知识库实体，不存在则返回 None
        """
        query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        if user_id is not None:
            query = query.where(KnowledgeBase.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_knowledge_base(self, kb_id: int, user_id: int) -> bool:
        """
        删除知识库（级联删除文档和分块）

        Args:
            kb_id: 知识库 ID
            user_id: 用户 ID

        Returns:
            是否删除成功
        """
        # 检查知识库是否存在且属于该用户
        kb = await self.get_knowledge_base(kb_id, user_id)
        if kb is None:
            return False

        # 删除分块
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.knowledge_base_id == kb_id))
        # 删除文档
        await self.db.execute(delete(Document).where(Document.knowledge_base_id == kb_id))
        # 删除知识库
        await self.db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        await self.db.commit()
        logger.info(f"Deleted knowledge base: {kb_id}")
        return True

    # ========== 文档管理 ==========

    async def create_document(
        self,
        knowledge_base_id: int,
        file_name: str,
        file_url: str,
        file_size: int | None = None,
        file_type: str | None = None,
    ) -> Document:
        """
        创建文档记录（上传后调用）

        Args:
            knowledge_base_id: 知识库 ID
            file_name: 原始文件名
            file_url: OSS URL
            file_size: 文件大小
            file_type: 文件类型

        Returns:
            创建的文档实体
        """
        doc = Document(
            id=generate_id(),
            knowledge_base_id=knowledge_base_id,
            file_name=file_name,
            file_url=file_url,
            file_size=file_size,
            file_type=file_type,
            status="pending",
        )
        self.db.add(doc)

        # 更新知识库文档计数
        await self.db.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == knowledge_base_id)
            .values(document_count=KnowledgeBase.document_count + 1)
        )

        await self.db.commit()
        await self.db.refresh(doc)
        logger.info(f"Created document: {doc.id} - {file_name}")
        return doc

    async def list_documents(
        self, knowledge_base_id: int, page_params: PageParams
    ) -> tuple[list[Document], int]:
        """
        列出知识库的所有文档（分页）

        Args:
            knowledge_base_id: 知识库 ID
            page_params: 分页参数

        Returns:
            (文档列表, 总记录数)
        """
        # 1. 查询总数
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
        )
        total = count_result.scalar() or 0

        # 2. 查询当页数据
        result = await self.db.execute(
            select(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
            .order_by(Document.create_time.desc())
            .limit(page_params.size)
            .offset(page_params.offset)
        )
        return list(result.scalars().all()), total

    async def get_document(self, doc_id: int) -> Document | None:
        """
        获取文档详情

        Args:
            doc_id: 文档 ID

        Returns:
            文档实体
        """
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def update_document_status(
        self,
        doc_id: int,
        status: str,
        chunk_count: int | None = None,
    ) -> None:
        """
        更新文档处理状态

        Args:
            doc_id: 文档 ID
            status: 新状态
            chunk_count: 分块数量（可选）
        """
        values: dict[str, Any] = {"status": status}
        if chunk_count is not None:
            values["chunk_count"] = chunk_count

        await self.db.execute(update(Document).where(Document.id == doc_id).values(**values))
        await self.db.commit()

    async def delete_document(self, doc_id: int) -> bool:
        """
        删除文档（级联删除分块）

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        doc = await self.get_document(doc_id)
        if doc is None:
            return False

        # 获取分块数量用于更新知识库统计
        chunk_count_result = await self.db.execute(
            select(func.count()).where(DocumentChunk.document_id == doc_id)
        )
        chunk_count = chunk_count_result.scalar() or 0

        # 删除分块
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))
        # 删除文档
        await self.db.execute(delete(Document).where(Document.id == doc_id))

        # 更新知识库统计
        await self.db.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == doc.knowledge_base_id)
            .values(
                document_count=KnowledgeBase.document_count - 1,
                chunk_count=KnowledgeBase.chunk_count - chunk_count,
            )
        )

        await self.db.commit()
        logger.info(f"Deleted document: {doc_id}")
        return True

    # ========== 分块管理 ==========

    async def create_chunks(
        self,
        knowledge_base_id: int,
        document_id: int,
        chunks: list[dict[str, Any]],
    ) -> int:
        """
        批量创建文档分块

        Args:
            knowledge_base_id: 知识库 ID
            document_id: 文档 ID
            chunks: 分块列表，每个包含 content, embedding, metadata

        Returns:
            创建的分块数量
        """
        chunk_entities = []
        for i, chunk in enumerate(chunks):
            chunk_entities.append(
                DocumentChunk(
                    id=generate_id(),
                    knowledge_base_id=knowledge_base_id,
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk["content"],
                    embedding=chunk.get("embedding"),
                    chunk_metadata=chunk.get("metadata"),
                )
            )

        self.db.add_all(chunk_entities)

        # 更新知识库分块计数
        await self.db.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == knowledge_base_id)
            .values(chunk_count=KnowledgeBase.chunk_count + len(chunks))
        )

        await self.db.commit()
        logger.info(f"Created {len(chunks)} chunks for document {document_id}")
        return len(chunks)

    async def get_chunks_by_document(self, document_id: int) -> list[DocumentChunk]:
        """
        获取文档的所有分块

        Args:
            document_id: 文档 ID

        Returns:
            分块列表
        """
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())
