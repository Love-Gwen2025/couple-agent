"""
文档分块实体模型

对应 t_document_chunk 表，存储文档分块内容和向量。
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DocumentChunk(Base):
    """
    文档分块实体

    存储文档解析后的分块内容及其向量表示。

    Attributes:
        knowledge_base_id: 所属知识库 ID
        document_id: 所属文档 ID
        chunk_index: 分块序号（从 0 开始）
        content: 分块文本内容
        embedding: 向量表示（512维，适配 bge-small-zh-v1.5）
        chunk_metadata: 元数据（页码、段落信息等）
    """

    __tablename__ = "t_document_chunk"

    # 所属知识库（冗余字段，便于按知识库检索）
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # 所属文档
    document_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # 分块序号
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 分块文本内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 向量表示（512维）
    embedding = mapped_column(Vector(512))
    # 元数据（页码、段落信息等）- 使用 chunk_metadata 避免与 SQLAlchemy 保留字冲突
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)

    def to_vo(self) -> dict:
        """
        转为接口返回的视图对象（不含向量）
        """
        return {
            "id": str(self.id),
            "documentId": str(self.document_id),
            "chunkIndex": self.chunk_index,
            "content": self.content,
            "metadata": self.chunk_metadata,
        }
