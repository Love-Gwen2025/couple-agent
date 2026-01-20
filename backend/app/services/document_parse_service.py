"""
文档解析服务

使用 LangChain 社区的 DocumentLoaders 和 TextSplitters 进行文档解析和分块。
支持 PDF、Word (docx)、TXT 格式。
"""

import tempfile
from pathlib import Path
from typing import Any

import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from app.core.settings import Settings
from app.services.embedding_service import EmbeddingService


class DocumentParseService:
    """
    文档解析服务

    使用 LangChain 社区库实现：
    1. DocumentLoaders - 解析各种格式文档
    2. RecursiveCharacterTextSplitter - 智能分块
    3. EmbeddingService - 向量化
    """

    def __init__(self, settings: Settings, embedding_service: EmbeddingService):
        """
        初始化文档解析服务

        Args:
            settings: 应用配置
            embedding_service: Embedding 服务
        """
        self.settings = settings
        self.embedding_service = embedding_service

        # 使用 LangChain 的递归字符分块器
        # 按优先级在这些分隔符处分割：段落 -> 换行 -> 句子 -> 词
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,  # 每个分块的最大字符数
            chunk_overlap=50,  # 分块之间的重叠字符数
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

    async def download_file(self, file_url: str) -> bytes:
        """
        从 URL 下载文件内容

        Args:
            file_url: 文件 URL（OSS 或其他）

        Returns:
            文件内容的字节数据
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(file_url)
            response.raise_for_status()
            return response.content

    def get_file_type(self, file_name: str) -> str:
        """
        根据文件名获取文件类型

        Args:
            file_name: 文件名

        Returns:
            文件类型
        """
        suffix = Path(file_name).suffix.lower().lstrip(".")
        if suffix == "pdf":
            return "pdf"
        elif suffix in ["docx", "doc"]:
            return "docx"
        elif suffix == "txt":
            return "txt"
        else:
            return suffix

    def _load_pdf(self, file_path: str) -> list[str]:
        """
        使用 LangChain 的 PyPDFLoader 加载 PDF

        Args:
            file_path: 本地文件路径

        Returns:
            页面文本列表
        """
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(file_path)
        pages = loader.load()
        return [page.page_content for page in pages if page.page_content.strip()]

    def _load_docx(self, file_path: str) -> list[str]:
        """
        使用 LangChain 的 Docx2txtLoader 加载 Word 文档

        Args:
            file_path: 本地文件路径

        Returns:
            文档文本列表
        """
        from langchain_community.document_loaders import Docx2txtLoader

        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        return [doc.page_content for doc in docs if doc.page_content.strip()]

    def _load_txt(self, file_path: str) -> list[str]:
        """
        使用 LangChain 的 TextLoader 加载 TXT 文件

        Args:
            file_path: 本地文件路径

        Returns:
            文本内容列表
        """
        from langchain_community.document_loaders import TextLoader

        # 尝试多种编码
        for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                loader = TextLoader(file_path, encoding=encoding)
                docs = loader.load()
                return [doc.page_content for doc in docs if doc.page_content.strip()]
            except Exception:
                continue

        # 最后使用默认编码并忽略错误
        loader = TextLoader(file_path, encoding="utf-8", autodetect_encoding=True)
        docs = loader.load()
        return [doc.page_content for doc in docs if doc.page_content.strip()]

    def load_document(self, file_path: str, file_type: str) -> list[str]:
        """
        根据文件类型加载文档

        Args:
            file_path: 本地文件路径
            file_type: 文件类型 (pdf/docx/txt)

        Returns:
            文档文本列表
        """
        file_type = file_type.lower()
        if file_type == "pdf":
            return self._load_pdf(file_path)
        elif file_type in ["docx", "doc"]:
            return self._load_docx(file_path)
        elif file_type == "txt":
            return self._load_txt(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

    def split_text(self, texts: list[str], file_name: str, file_type: str) -> list[dict[str, Any]]:
        """
        使用 RecursiveCharacterTextSplitter 智能分块

        Args:
            texts: 文档文本列表（每个元素可能是一页或一段）
            file_name: 原始文件名（用于 metadata）
            file_type: 文件类型

        Returns:
            分块列表，每个包含 content 和 metadata
        """
        # 合并所有文本
        full_text = "\n\n".join(texts)

        if not full_text.strip():
            return []

        # 使用 LangChain 分块器分块
        chunks = self.text_splitter.split_text(full_text)

        # 构建结果
        result = []
        for i, chunk_text in enumerate(chunks):
            if chunk_text.strip():
                result.append(
                    {
                        "content": chunk_text.strip(),
                        "metadata": {
                            "file_name": file_name,
                            "file_type": file_type,
                            "chunk_index": i,
                            "chunk_method": "recursive_character",
                        },
                    }
                )

        return result

    async def process_document(
        self,
        file_url: str,
        file_name: str,
        file_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        完整处理文档：下载 -> 解析 -> 分块 -> 向量化

        Args:
            file_url: 文件 URL
            file_name: 原始文件名
            file_type: 文件类型（可选，将从文件名推断）

        Returns:
            处理后的分块列表，每个包含 content, embedding, metadata
        """
        # 确定文件类型
        if not file_type:
            file_type = self.get_file_type(file_name)

        logger.info(f"Processing document: {file_name} ({file_type})")

        # 下载文件
        content = await self.download_file(file_url)
        logger.info(f"Downloaded {len(content)} bytes")

        # 创建临时文件（LangChain Loaders 需要文件路径）
        suffix = f".{file_type}" if file_type else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # 使用 LangChain Loader 解析文档
            texts = self.load_document(tmp_path, file_type)
            logger.info(f"Loaded {len(texts)} text segments")

            # 使用 RecursiveCharacterTextSplitter 分块
            chunks = self.split_text(texts, file_name, file_type)
            logger.info(f"Split into {len(chunks)} chunks")

            if not chunks:
                return []

            # 向量化
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = await self.embedding_service.embed_texts(chunk_texts)

            # 合并结果
            for i, chunk in enumerate(chunks):
                chunk["embedding"] = embeddings[i]

            logger.info(f"Document processing complete: {len(chunks)} chunks with embeddings")
            return chunks

        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)
