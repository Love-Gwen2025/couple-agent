"""
知识库实体模型

对应 t_knowledge_base 表，存储知识库元信息。
"""

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KnowledgeBase(Base):
    """
    知识库实体

    Attributes:
        user_id: 所属用户 ID
        name: 知识库名称
        description: 知识库描述
        document_count: 文档数量
        chunk_count: 分块总数
    """

    __tablename__ = "t_knowledge_base"

    # 所属用户
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # 知识库名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 知识库描述
    description: Mapped[str | None] = mapped_column(Text)
    # 文档数量（冗余字段，便于查询）
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    # 分块总数（冗余字段，便于查询）
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    def to_vo(self) -> dict:
        """
        转为接口返回的视图对象
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "documentCount": self.document_count,
            "chunkCount": self.chunk_count,
            "createTime": self.create_time.isoformat() if self.create_time else None,
            "updateTime": self.update_time.isoformat() if self.update_time else None,
        }
