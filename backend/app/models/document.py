"""
文档实体模型

对应 t_document 表，存储上传文档的元信息和 OSS URL。
"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Document(Base):
    """
    文档实体

    存储上传到知识库的文档元信息，原始文件存储在 OSS。

    Attributes:
        knowledge_base_id: 所属知识库 ID
        file_name: 原始文件名
        file_url: OSS 存储 URL
        file_size: 文件大小（字节）
        file_type: 文件类型 (pdf/docx/txt)
        chunk_count: 分块数量
        status: 处理状态 (pending/processing/done/failed)
    """

    __tablename__ = "t_document"

    # 所属知识库
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # 原始文件名
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # OSS 存储 URL
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    # 文件大小（字节）
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    # 文件类型
    file_type: Mapped[str | None] = mapped_column(String(50))
    # 分块数量
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # 处理状态：pending（待处理）, processing（处理中）, done（完成）, failed（失败）
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    def to_vo(self) -> dict:
        """
        转为接口返回的视图对象
        """
        return {
            "id": str(self.id),
            "fileName": self.file_name,
            "fileUrl": self.file_url,
            "fileSize": self.file_size,
            "fileType": self.file_type,
            "chunkCount": self.chunk_count,
            "status": self.status,
            "createTime": self.create_time.isoformat() if self.create_time else None,
        }
