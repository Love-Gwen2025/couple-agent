"""
Embedding 服务 - 支持本地模型和远程 API

支持两种模式：
1. 本地模型 (bge-small-zh-v1.5) - 免费、隐私安全、无网络延迟
2. 远程 API (OpenAI/DeepSeek) - 效果好，需要 API Key
"""

from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.models.message_embedding import MessageEmbedding


class EmbeddingService:
    """
    1. 生成文本 embedding
    2. 存储到 pgvector
    3. 语义检索相关消息
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.dimension = settings.ai_embedding_dimension
        self._model = None
        self._embeddings = None

        # 根据配置选择模型类型
        self.use_local = settings.ai_embedding_provider == "local"

    def warmup(self) -> None:
        """预加载模型（应用启动时调用）"""
        if self.use_local:
            self._get_local_model()

    def _get_local_model(self):
        """
        延迟加载本地 Embedding 模型 (使用 fastembed，比 sentence-transformers 更轻量)
        fastembed 使用 ONNX Runtime，无需 PyTorch，镜像大小从 11GB 降至 ~500MB
        """
        if self._model is None:
            from fastembed import TextEmbedding

            model_name = self.settings.ai_embedding_model
            logger.info(f"Loading local embedding model (fastembed): {model_name}")
            # fastembed 会自动下载并缓存模型到 ~/.cache/fastembed
            self._model = TextEmbedding(model_name=model_name)
            logger.info("Embedding model loaded successfully")

        return self._model

    def _get_remote_embeddings(self):
        """
        获取远程 Embedding 客户端
        """
        if self._embeddings is None:
            from langchain_openai import OpenAIEmbeddings

            api_key = self.settings.ai_embedding_api_key
            base_url = self.settings.ai_embedding_base_url

            self._embeddings = OpenAIEmbeddings(
                model=self.settings.ai_embedding_model,
                api_key=api_key,
                base_url=base_url,
            )

        return self._embeddings

    async def embed_text(self, text: str) -> list[float]:
        """
        生成文本的 embedding 向量
        """
        if self.use_local:
            model = self._get_local_model()
            # fastembed.embed() 返回生成器，需要转换为 list 取第一个结果
            vectors = list(model.embed([text]))
            return vectors[0].tolist()
        else:
            embeddings = self._get_remote_embeddings()
            return await embeddings.aembed_query(text)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成 embedding
        """
        if self.use_local:
            model = self._get_local_model()
            # fastembed.embed() 返回生成器，批量转换为列表
            vectors = list(model.embed(texts))
            return [v.tolist() for v in vectors]
        else:
            embeddings = self._get_remote_embeddings()
            return await embeddings.aembed_documents(texts)

    async def store_message_embedding(
        self,
        db: AsyncSession,
        message_id: int,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
    ) -> MessageEmbedding:
        """
        为消息生成 embedding 并存储
        """
        # 生成向量
        vector = await self.embed_text(content)

        # 存储
        embedding = MessageEmbedding(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            embedding=vector,
        )
        db.add(embedding)
        await db.commit()
        await db.refresh(embedding)
        return embedding

    async def search_similar(
        self,
        db: AsyncSession,
        query: str,
        conversation_id: int | None = None,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        语义检索相关消息

        Args:
            db: 数据库会话
            query: 查询文本
            conversation_id: 可选的会话 ID 过滤
            top_k: 返回最相似的 K 条结果
            similarity_threshold: 相似度阈值，低于此值的结果将被过滤

        返回: [{"content": str, "role": str, "similarity": float}, ...]
        """
        # 生成查询向量
        query_vector = await self.embed_text(query)

        # 构建查询 - 使用余弦相似度
        # 使用 JSON 格式传递向量，避免 SQL 注入
        import json

        query_vec_json = json.dumps(query_vector)

        if conversation_id:
            sql = text("""
                SELECT
                    content,
                    role,
                    1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
                FROM t_message_embedding
                WHERE conversation_id = :conv_id
                ORDER BY embedding <=> CAST(:query_vec AS vector)
                LIMIT :limit
            """)
            params = {
                "query_vec": query_vec_json,
                "conv_id": conversation_id,
                "limit": top_k,
            }
        else:
            sql = text("""
                SELECT
                    content,
                    role,
                    1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
                FROM t_message_embedding
                ORDER BY embedding <=> CAST(:query_vec AS vector)
                LIMIT :limit
            """)
            params = {
                "query_vec": query_vec_json,
                "limit": top_k,
            }

        result = await db.execute(sql, params)
        rows = result.fetchall()

        # 过滤低于阈值的结果
        return [
            {"content": row.content, "role": row.role, "similarity": float(row.similarity)}
            for row in rows
            if float(row.similarity) >= similarity_threshold
        ]

    # ========== 知识库检索方法 ==========

    async def search_knowledge_base(
        self,
        db: AsyncSession,
        query: str,
        knowledge_base_ids: list[int],
        top_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        在知识库中进行向量检索

        Args:
            db: 数据库会话
            query: 查询文本
            knowledge_base_ids: 知识库 ID 列表
            top_k: 返回最相似的 K 条结果
            similarity_threshold: 相似度阈值

        Returns:
            [{content, similarity, document_id, chunk_index, metadata}, ...]
        """
        import json

        # 生成查询向量
        query_vector = await self.embed_text(query)
        query_vec_json = json.dumps(query_vector)

        # 构建 SQL 查询
        sql = text("""
            SELECT
                c.content,
                c.document_id,
                c.chunk_index,
                c.metadata,
                d.file_name,
                1 - (c.embedding <=> CAST(:query_vec AS vector)) as similarity
            FROM t_document_chunk c
            JOIN t_document d ON c.document_id = d.id
            WHERE c.knowledge_base_id = ANY(:kb_ids)
            ORDER BY c.embedding <=> CAST(:query_vec AS vector)
            LIMIT :limit
        """)

        result = await db.execute(
            sql,
            {
                "query_vec": query_vec_json,
                "kb_ids": knowledge_base_ids,
                "limit": top_k,
            },
        )
        rows = result.fetchall()

        # 过滤并格式化结果
        return [
            {
                "content": row.content,
                "similarity": float(row.similarity),
                "document_id": str(row.document_id),
                "chunk_index": row.chunk_index,
                "file_name": row.file_name,
                "metadata": row.metadata,
            }
            for row in rows
            if float(row.similarity) >= similarity_threshold
        ]

    async def hybrid_search_knowledge_base(
        self,
        db: AsyncSession,
        query: str,
        knowledge_base_ids: list[int],
        top_k: int = 5,
        similarity_threshold: float = 0.5,
        mode: str = "union",  # union（并集）或 intersection（交集）
    ) -> list[dict[str, Any]]:
        """
        混合检索：向量检索 + BM25 关键词检索

        Args:
            db: 数据库会话
            query: 查询文本
            knowledge_base_ids: 知识库 ID 列表
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
            mode: 合并模式 (union=并集, intersection=交集)

        Returns:
            融合排序后的结果列表
        """
        import jieba
        from rank_bm25 import BM25Okapi

        # 1. 向量检索
        vector_results = await self.search_knowledge_base(
            db=db,
            query=query,
            knowledge_base_ids=knowledge_base_ids,
            top_k=top_k * 2,  # 多取一些用于融合
            similarity_threshold=similarity_threshold,
        )

        # 2. 获取所有文档分块用于 BM25
        sql = text("""
            SELECT c.id, c.content, c.document_id, c.chunk_index, c.metadata, d.file_name
            FROM t_document_chunk c
            JOIN t_document d ON c.document_id = d.id
            WHERE c.knowledge_base_id = ANY(:kb_ids)
        """)
        result = await db.execute(sql, {"kb_ids": knowledge_base_ids})
        all_chunks = result.fetchall()

        if not all_chunks:
            return vector_results[:top_k]

        # 3. BM25 检索
        # 分词
        tokenized_corpus = [list(jieba.cut(chunk.content)) for chunk in all_chunks]
        tokenized_query = list(jieba.cut(query))

        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(tokenized_query)

        # 获取 BM25 top-k
        bm25_top_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[: top_k * 2]

        bm25_results = []
        max_bm25_score = max(bm25_scores) if bm25_scores.any() else 1
        for idx in bm25_top_indices:
            chunk = all_chunks[idx]
            # 归一化 BM25 分数到 0-1
            normalized_score = bm25_scores[idx] / max_bm25_score if max_bm25_score > 0 else 0
            bm25_results.append(
                {
                    "content": chunk.content,
                    "similarity": normalized_score,
                    "document_id": str(chunk.document_id),
                    "chunk_index": chunk.chunk_index,
                    "file_name": chunk.file_name,
                    "metadata": chunk.metadata,
                    "source": "bm25",
                }
            )

        # 4. 融合结果
        # 使用 Reciprocal Rank Fusion (RRF) 算法
        k = 60  # RRF 常数

        # 计算 RRF 分数
        rrf_scores: dict[str, float] = {}
        content_map: dict[str, dict] = {}

        # 向量检索结果
        for rank, item in enumerate(vector_results):
            key = f"{item['document_id']}_{item['chunk_index']}"
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k + rank + 1)
            item["source"] = "vector"
            content_map[key] = item

        # BM25 结果
        for rank, item in enumerate(bm25_results):
            key = f"{item['document_id']}_{item['chunk_index']}"
            rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k + rank + 1)
            if key not in content_map:
                content_map[key] = item

        # 根据模式过滤
        if mode == "intersection":
            # 交集：只保留两种方法都检索到的结果
            vector_keys = {f"{r['document_id']}_{r['chunk_index']}" for r in vector_results}
            bm25_keys = {f"{r['document_id']}_{r['chunk_index']}" for r in bm25_results}
            valid_keys = vector_keys & bm25_keys
            rrf_scores = {k: v for k, v in rrf_scores.items() if k in valid_keys}

        # 按 RRF 分数排序
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 构建最终结果
        final_results = []
        for key in sorted_keys[:top_k]:
            item = content_map[key]
            item["rrf_score"] = rrf_scores[key]
            final_results.append(item)

        logger.info(
            f"Hybrid search: vector={len(vector_results)}, bm25={len(bm25_results)}, "
            f"final={len(final_results)} (mode={mode})"
        )

        return final_results
