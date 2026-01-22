"""
Rerank 重排序服务

使用 Cross-Encoder 模型对初筛结果进行精细排序，
提高检索结果的精准度。

支持多种 Rerank 策略：
1. Cross-Encoder（BGE-Reranker）- 最精准
2. LLM Rerank - 使用大模型打分
3. Cohere Rerank API - 云端服务
"""

from enum import Enum
from typing import Any

from loguru import logger


class RerankStrategy(str, Enum):
    """重排序策略枚举"""

    CROSS_ENCODER = "cross_encoder"  # 使用 Cross-Encoder 模型
    LLM = "llm"  # 使用 LLM 打分
    DISABLED = "disabled"  # 禁用重排序


class RerankService:
    """
    重排序服务

    使用 Cross-Encoder 或 LLM 对检索结果进行二次排序，
    提高最终结果的相关性。
    """

    def __init__(
        self,
        strategy: RerankStrategy = RerankStrategy.CROSS_ENCODER,
        model_name: str = "BAAI/bge-reranker-base",
        llm=None,
    ):
        """
        初始化重排序服务

        Args:
            strategy: 重排序策略
            model_name: Cross-Encoder 模型名称
            llm: 可选的 LLM 模型（用于 LLM 策略）
        """
        self.strategy = strategy
        self.model_name = model_name
        self.llm = llm
        self._cross_encoder = None

    def _get_cross_encoder(self):
        """延迟加载 Cross-Encoder 模型"""
        if self._cross_encoder is None:
            try:
                from sentence_transformers import CrossEncoder

                logger.info(f"Loading Cross-Encoder model: {self.model_name}")
                self._cross_encoder = CrossEncoder(self.model_name)
                logger.info("Cross-Encoder model loaded successfully")
            except ImportError:
                logger.error(
                    "sentence-transformers not installed. "
                    "Install it with: pip install sentence-transformers"
                )
                raise
        return self._cross_encoder

    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        对检索结果进行重排序

        Args:
            query: 用户查询
            results: 初筛检索结果列表，每个结果必须包含 'content' 字段
            top_k: 返回前 K 个结果
            score_threshold: 分数阈值，低于此值的结果会被过滤

        Returns:
            重排序后的结果列表，每个结果会增加 'rerank_score' 字段
        """
        if not results:
            return []

        if self.strategy == RerankStrategy.DISABLED:
            logger.debug("Reranking disabled, returning original results")
            return results[:top_k]

        if self.strategy == RerankStrategy.CROSS_ENCODER:
            return await self._rerank_with_cross_encoder(query, results, top_k, score_threshold)
        elif self.strategy == RerankStrategy.LLM:
            return await self._rerank_with_llm(query, results, top_k, score_threshold)
        else:
            return results[:top_k]

    async def _rerank_with_cross_encoder(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
        score_threshold: float,
    ) -> list[dict[str, Any]]:
        """使用 Cross-Encoder 进行重排序"""
        import asyncio

        try:
            model = self._get_cross_encoder()

            # Cross-Encoder 需要 (query, document) 对
            pairs = [(query, r["content"]) for r in results]

            # 在线程池中运行同步 predict 方法
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, model.predict, pairs)

            # 添加重排序分数
            for i, result in enumerate(results):
                result["rerank_score"] = float(scores[i])

            # 按重排序分数排序
            sorted_results = sorted(results, key=lambda x: x["rerank_score"], reverse=True)

            # 过滤低分结果
            filtered_results = [r for r in sorted_results if r["rerank_score"] >= score_threshold]

            logger.info(
                f"🎯 Cross-Encoder rerank: {len(results)} -> {len(filtered_results[:top_k])} results"
            )

            return filtered_results[:top_k]

        except Exception as e:
            logger.error(f"Cross-Encoder reranking failed: {e}")
            return results[:top_k]

    async def _rerank_with_llm(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
        score_threshold: float,
    ) -> list[dict[str, Any]]:
        """使用 LLM 进行重排序"""
        if not self.llm:
            logger.warning("LLM not configured for reranking, returning original results")
            return results[:top_k]

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            # 构建评分 Prompt
            scored_results = []

            for result in results:
                content = result["content"][:500]  # 限制长度

                prompt = f"""请评估以下文档片段与查询的相关性，给出 0-10 的评分。

查询：{query}

文档片段：
{content}

只输出一个数字评分（0-10），不要输出其他内容。

评分："""

                response = await self.llm.ainvoke(
                    [
                        SystemMessage(content="你是一个文档相关性评估专家。"),
                        HumanMessage(content=prompt),
                    ]
                )

                try:
                    score = float(response.content.strip()) / 10.0  # 归一化到 0-1
                except ValueError:
                    score = 0.5  # 解析失败给中间分

                result["rerank_score"] = score
                if score >= score_threshold:
                    scored_results.append(result)

            # 排序
            sorted_results = sorted(scored_results, key=lambda x: x["rerank_score"], reverse=True)

            logger.info(f"🎯 LLM rerank: {len(results)} -> {len(sorted_results[:top_k])} results")

            return sorted_results[:top_k]

        except Exception as e:
            logger.error(f"LLM reranking failed: {e}")
            return results[:top_k]


# 全局单例（可选）
_rerank_service: RerankService | None = None


def get_rerank_service(
    strategy: RerankStrategy = RerankStrategy.CROSS_ENCODER,
    model_name: str = "BAAI/bge-reranker-base",
) -> RerankService:
    """获取重排序服务单例"""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService(strategy=strategy, model_name=model_name)
    return _rerank_service
