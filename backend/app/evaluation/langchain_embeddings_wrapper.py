"""
EmbeddingService 的 LangChain 包装器

将我们的 EmbeddingService 包装成 LangChain Embeddings 接口，
使其能够被 RAGAS 等需要 LangChain Embeddings 的工具使用。
"""

import asyncio

from langchain_core.embeddings import Embeddings

from app.services.embedding_service import EmbeddingService


class LangChainEmbeddingsWrapper(Embeddings):
    """
    将 EmbeddingService 包装为 LangChain Embeddings 接口

    RAGAS 内部使用 LangChain Embeddings 接口，这个包装器使得
    我们的本地 EmbeddingService 能够与 RAGAS 无缝集成。

    使用方法:
        embedding_service = EmbeddingService(settings)
        langchain_embeddings = LangChainEmbeddingsWrapper(embedding_service)

        # 传给 RAGAS
        from ragas import evaluate
        result = evaluate(dataset, metrics, embeddings=langchain_embeddings)
    """

    def __init__(self, embedding_service: EmbeddingService):
        """
        初始化包装器

        Args:
            embedding_service: 我们自己的 EmbeddingService 实例
        """
        self.embedding_service = embedding_service

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        嵌入文档列表（同步方法，内部调用异步方法）

        Args:
            texts: 要嵌入的文本列表

        Returns:
            嵌入向量列表
        """
        # LangChain 的 embed_documents 是同步方法
        # 需要用 asyncio.run 或 get_event_loop 来调用异步方法
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，使用 run_coroutine_threadsafe

                future = asyncio.run_coroutine_threadsafe(
                    self.embedding_service.embed_texts(texts), loop
                )
                return future.result(timeout=60)
            else:
                return loop.run_until_complete(self.embedding_service.embed_texts(texts))
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(self.embedding_service.embed_texts(texts))

    def embed_query(self, text: str) -> list[float]:
        """
        嵌入单个查询（同步方法，内部调用异步方法）

        Args:
            text: 要嵌入的文本

        Returns:
            嵌入向量
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():

                future = asyncio.run_coroutine_threadsafe(
                    self.embedding_service.embed_text(text), loop
                )
                return future.result(timeout=60)
            else:
                return loop.run_until_complete(self.embedding_service.embed_text(text))
        except RuntimeError:
            return asyncio.run(self.embedding_service.embed_text(text))

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        异步嵌入文档列表

        Args:
            texts: 要嵌入的文本列表

        Returns:
            嵌入向量列表
        """
        return await self.embedding_service.embed_texts(texts)

    async def aembed_query(self, text: str) -> list[float]:
        """
        异步嵌入单个查询

        Args:
            text: 要嵌入的文本

        Returns:
            嵌入向量
        """
        return await self.embedding_service.embed_text(text)
