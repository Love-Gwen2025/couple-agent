"""
RAG 质量评估器 - 基于 RAGAS 框架

功能：
1. 集成 RAGAS 框架，支持标准化评估指标
2. 支持生成质量评估（忠实度、答案相关性）
3. 支持端到端 RAG 流程评估（检索 + 生成）
4. 支持 Ground Truth 标注（可选）

使用方式：
    from app.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator(embedding_service, model)
    result = await evaluator.evaluate_rag_pipeline(...)
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from datasets import Dataset
from langchain_core.language_models import BaseChatModel
from loguru import logger
from ragas import evaluate
from ragas.metrics import (
    answer_correctness,
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.langchain_embeddings_wrapper import LangChainEmbeddingsWrapper
from app.services.embedding_service import EmbeddingService


@dataclass
class RAGPipelineMetrics:
    """端到端 RAG 流程评估指标"""

    query: str
    # 检索指标
    num_retrieved: int
    retrieval_latency_ms: float
    avg_similarity: float
    # 生成结果
    generated_answer: str | None = None  # 生成的答案
    retrieved_contexts: list[str] = field(default_factory=list)  # 检索到的上下文
    # RAGAS 标准指标
    faithfulness_score: float | None = None  # 忠实度（0-1）
    answer_relevancy_score: float | None = None  # 答案相关性（0-1）
    context_precision_score: float | None = None  # 上下文精确度（0-1）
    context_recall_score: float | None = None  # 上下文召回率（0-1，需要 Ground Truth）
    answer_correctness_score: float | None = None  # 答案正确性（0-1，需要 Ground Truth）
    # 性能指标
    total_latency_ms: float = 0.0


@dataclass
class BatchEvaluationReport:
    """批量评估报告"""

    total_queries: int = 0
    # 检索指标汇总
    avg_retrieval_latency: float = 0.0
    avg_similarity: float = 0.0
    # RAGAS 指标汇总
    avg_faithfulness: float = 0.0
    avg_answer_relevancy: float = 0.0
    avg_context_precision: float = 0.0
    avg_context_recall: float = 0.0
    avg_answer_correctness: float = 0.0
    # 详细指标
    metrics_list: list[RAGPipelineMetrics] = field(default_factory=list)


class RAGEvaluator:
    """
    RAG 质量评估器 - 基于 RAGAS 框架

    功能：
    1. 检索质量评估
    2. 生成质量评估（RAGAS）
    3. 端到端 RAG 流程评估
    4. 方法对比（基础 vs 高级）
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        model: BaseChatModel | None = None,
    ):
        """
        初始化评估器

        Args:
            embedding_service: Embedding 服务实例
            model: LLM 模型（用于生成和评估）
        """
        self.embedding_service = embedding_service
        self.model = model
        # 创建 LangChain Embeddings 包装器，用于 RAGAS 评估
        self._langchain_embeddings = LangChainEmbeddingsWrapper(embedding_service)

    async def evaluate_rag_pipeline(
        self,
        db: AsyncSession,
        query: str,
        knowledge_base_ids: list[int],
        use_advanced: bool = False,
        ground_truth_answer: str | None = None,
        ground_truth_contexts: list[str] | None = None,
        skip_slow_metrics: bool = False,
    ) -> RAGPipelineMetrics:
        """
        评估完整的 RAG 流程（检索 + 生成）

        Args:
            db: 数据库会话
            query: 用户查询
            knowledge_base_ids: 知识库 ID 列表
            use_advanced: 是否使用高级检索
            ground_truth_answer: 标准答案（可选，用于计算 answer_correctness）
            ground_truth_contexts: 标准上下文列表（可选，用于计算 context_recall）

        Returns:
            RAG 流程评估指标
        """
        total_start = time.time()

        # 1. 执行检索
        retrieval_start = time.time()
        if use_advanced:
            results = await self.embedding_service.advanced_search_knowledge_base(
                db=db,
                query=query,
                knowledge_base_ids=knowledge_base_ids,
                top_k=5,
                enable_query_rewrite=True,
                enable_rerank=True,
                model=self.model,
            )
        else:
            results = await self.embedding_service.hybrid_search_knowledge_base(
                db=db,
                query=query,
                knowledge_base_ids=knowledge_base_ids,
                top_k=5,
            )
        retrieval_latency = (time.time() - retrieval_start) * 1000

        if not results:
            logger.warning(f"No retrieval results for query: {query}")
            return RAGPipelineMetrics(
                query=query,
                num_retrieved=0,
                retrieval_latency_ms=retrieval_latency,
                avg_similarity=0.0,
                total_latency_ms=(time.time() - total_start) * 1000,
            )

        # 提取检索的上下文
        retrieved_contexts = [r["content"] for r in results]
        avg_similarity = sum(r.get("rerank_score", r.get("similarity", 0)) for r in results) / len(
            results
        )

        # 2. 生成答案
        if not self.model:
            logger.warning("No model provided, skipping generation evaluation")
            return RAGPipelineMetrics(
                query=query,
                num_retrieved=len(results),
                retrieval_latency_ms=retrieval_latency,
                avg_similarity=avg_similarity,
                total_latency_ms=(time.time() - total_start) * 1000,
            )

        # 构建带上下文的 prompt
        context_text = "\n\n".join(
            [f"[文档 {i + 1}]\n{ctx}" for i, ctx in enumerate(retrieved_contexts)]
        )
        prompt = f"""基于以下参考资料回答问题。

参考资料：
{context_text}

问题：{query}

请根据参考资料给出准确、相关的回答。"""

        from langchain_core.messages import HumanMessage

        response = await self.model.ainvoke([HumanMessage(content=prompt)])
        # 使用通用工具函数处理 Gemini 等模型的列表格式响应
        from app.utils.content import extract_text_content

        generated_answer = extract_text_content(response.content)

        # 3. 使用 RAGAS 评估
        ragas_metrics = await self._evaluate_with_ragas(
            query=query,
            contexts=retrieved_contexts,
            answer=generated_answer,
            ground_truth_answer=ground_truth_answer,
            ground_truth_contexts=ground_truth_contexts,
            skip_slow_metrics=skip_slow_metrics,
        )

        total_latency = (time.time() - total_start) * 1000

        return RAGPipelineMetrics(
            query=query,
            num_retrieved=len(results),
            retrieval_latency_ms=retrieval_latency,
            avg_similarity=avg_similarity,
            generated_answer=generated_answer,
            retrieved_contexts=retrieved_contexts,
            faithfulness_score=ragas_metrics.get("faithfulness"),
            answer_relevancy_score=ragas_metrics.get("answer_relevancy"),
            context_precision_score=ragas_metrics.get("context_precision"),
            context_recall_score=ragas_metrics.get("context_recall"),
            answer_correctness_score=ragas_metrics.get("answer_correctness"),
            total_latency_ms=total_latency,
        )

    async def _evaluate_with_ragas(
        self,
        query: str,
        contexts: list[str],
        answer: str,
        ground_truth_answer: str | None = None,
        ground_truth_contexts: list[str] | None = None,
        skip_slow_metrics: bool = False,
    ) -> dict[str, float]:
        """
        使用 RAGAS 框架评估 RAG 质量

        Args:
            query: 用户查询
            contexts: 检索到的上下文列表
            answer: 生成的答案
            ground_truth_answer: 标准答案（可选）
            ground_truth_contexts: 标准上下文（可选）
            skip_slow_metrics: 跳过慢速指标（answer_relevancy，会超时）

        Returns:
            RAGAS 评估指标字典
        """
        # 构建 RAGAS 数据集
        data = {
            "question": [query],
            "contexts": [contexts],
            "answer": [answer],
        }

        # 根据是否有 Ground Truth 选择指标
        # 注意：context_precision 和 context_recall 需要 reference（ground_truth）
        metrics = [
            faithfulness,  # 忠实度（生成内容是否忠于上下文）- 快速
        ]

        # answer_relevancy 需要多次模型调用，经常超时，默认跳过
        if not skip_slow_metrics:
            metrics.append(answer_relevancy)  # 答案相关性（答案是否回答问题）- 慢速

        # 如果有 Ground Truth，添加需要 reference 的指标
        if ground_truth_contexts:
            data["ground_truth"] = ground_truth_contexts
            metrics.append(context_precision)  # 上下文精确度（需要 reference）
            metrics.append(context_recall)  # 上下文召回率（需要 reference）

        if ground_truth_answer:
            if "ground_truth" not in data:
                data["ground_truth"] = [ground_truth_answer]
            metrics.append(context_precision)  # 上下文精确度（需要 reference）
            metrics.append(answer_correctness)  # 答案正确性（需要 reference）

        # 转换为 RAGAS Dataset 格式
        dataset = Dataset.from_dict(data)

        # 执行评估
        # 注意：需要传入 LLM 模型，否则 RAGAS 会默认使用 OpenAI（需要 OPENAI_API_KEY）
        try:
            if self.model:
                # 使用用户配置的 LLM 和 Embeddings 进行评估
                # 必须同时传入 llm 和 embeddings，否则 RAGAS 会使用默认的 OpenAI
                result = evaluate(
                    dataset=dataset,
                    metrics=metrics,
                    llm=self.model,
                    embeddings=self._langchain_embeddings,
                )
            else:
                # 没有配置模型时，无法进行 RAGAS 评估
                logger.warning("No LLM model provided, skipping RAGAS evaluation")
                return {}

            logger.info(f"RAGAS evaluation result: {result}")

            # RAGAS evaluate() 返回 EvaluationResult 对象
            # 需要将其转换为字典格式以便后续处理
            # EvaluationResult 可以直接转换为 DataFrame，或取其分数
            if hasattr(result, "to_pandas"):
                # 转换为 DataFrame 然后取第一行（因为我们只评估一个样本）
                df = result.to_pandas()
                if len(df) > 0:
                    # 将 DataFrame 的第一行转换为字典
                    return df.iloc[0].to_dict()

            # 如果无法转换，尝试直接作为字典返回
            if isinstance(result, dict):
                return result

            # 最后尝试获取 scores 属性（某些 RAGAS 版本可能有这个）
            if hasattr(result, "scores"):
                return dict(result.scores)

            logger.warning(f"Unable to parse RAGAS result: {type(result)}")
            return {}

        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            return {}

    async def evaluate_batch(
        self,
        db: AsyncSession,
        test_cases: list[dict],
        use_advanced: bool = False,
        skip_slow_metrics: bool = False,
    ) -> BatchEvaluationReport:
        """
        批量评估多个测试用例

        Args:
            db: 数据库会话
            test_cases: 测试用例列表，每个用例包含：
                - query: 查询文本
                - knowledge_base_ids: 知识库 ID 列表
                - ground_truth_answer: 标准答案（可选）
                - ground_truth_contexts: 标准上下文（可选）
            use_advanced: 是否使用高级检索
            skip_slow_metrics: 跳过慢速评估指标

        Returns:
            批量评估报告
        """
        report = BatchEvaluationReport()
        report.total_queries = len(test_cases)

        logger.info(f"📊 Starting batch evaluation: {len(test_cases)} test cases")

        for i, case in enumerate(test_cases, 1):
            logger.info(f"⏳ Evaluating case {i}/{len(test_cases)}: {case['query'][:50]}...")

            metrics = await self.evaluate_rag_pipeline(
                db=db,
                query=case["query"],
                knowledge_base_ids=case.get("knowledge_base_ids", []),
                use_advanced=use_advanced,
                ground_truth_answer=case.get("ground_truth_answer"),
                ground_truth_contexts=case.get("ground_truth_contexts"),
                skip_slow_metrics=skip_slow_metrics,
            )

            report.metrics_list.append(metrics)

            # 避免 API 限流
            await asyncio.sleep(0.5)

        # 计算汇总指标
        if report.metrics_list:
            report.avg_retrieval_latency = sum(
                m.retrieval_latency_ms for m in report.metrics_list
            ) / len(report.metrics_list)

            report.avg_similarity = sum(m.avg_similarity for m in report.metrics_list) / len(
                report.metrics_list
            )

            # RAGAS 指标（过滤掉 None 值）
            faithfulness_scores = [
                m.faithfulness_score for m in report.metrics_list if m.faithfulness_score
            ]
            if faithfulness_scores:
                report.avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)

            relevancy_scores = [
                m.answer_relevancy_score for m in report.metrics_list if m.answer_relevancy_score
            ]
            if relevancy_scores:
                report.avg_answer_relevancy = sum(relevancy_scores) / len(relevancy_scores)

            precision_scores = [
                m.context_precision_score for m in report.metrics_list if m.context_precision_score
            ]
            if precision_scores:
                report.avg_context_precision = sum(precision_scores) / len(precision_scores)

            recall_scores = [
                m.context_recall_score for m in report.metrics_list if m.context_recall_score
            ]
            if recall_scores:
                report.avg_context_recall = sum(recall_scores) / len(recall_scores)

            correctness_scores = [
                m.answer_correctness_score
                for m in report.metrics_list
                if m.answer_correctness_score
            ]
            if correctness_scores:
                report.avg_answer_correctness = sum(correctness_scores) / len(correctness_scores)

        logger.info("✅ Batch evaluation completed")
        return report

    async def compare_methods(
        self,
        db: AsyncSession,
        test_cases: list[dict],
        skip_slow_metrics: bool = False,
    ) -> dict[str, Any]:
        """
        对比基础检索 vs 高级检索的效果

        Args:
            db: 数据库会话
            test_cases: 测试用例列表
            skip_slow_metrics: 跳过慢速评估指标

        Returns:
            对比结果
        """
        logger.info("📊 Evaluating baseline (hybrid search)...")
        baseline = await self.evaluate_batch(
            db=db, test_cases=test_cases, use_advanced=False, skip_slow_metrics=skip_slow_metrics
        )

        logger.info("📊 Evaluating advanced (query rewrite + rerank)...")
        advanced = await self.evaluate_batch(
            db=db, test_cases=test_cases, use_advanced=True, skip_slow_metrics=skip_slow_metrics
        )

        comparison = {
            "baseline": {
                "avg_similarity": baseline.avg_similarity,
                "avg_retrieval_latency": baseline.avg_retrieval_latency,
                "avg_faithfulness": baseline.avg_faithfulness,
                "avg_answer_relevancy": baseline.avg_answer_relevancy,
                "avg_context_precision": baseline.avg_context_precision,
            },
            "advanced": {
                "avg_similarity": advanced.avg_similarity,
                "avg_retrieval_latency": advanced.avg_retrieval_latency,
                "avg_faithfulness": advanced.avg_faithfulness,
                "avg_answer_relevancy": advanced.avg_answer_relevancy,
                "avg_context_precision": advanced.avg_context_precision,
            },
            "improvement": {
                "similarity_delta": advanced.avg_similarity - baseline.avg_similarity,
                "latency_delta": advanced.avg_retrieval_latency - baseline.avg_retrieval_latency,
                "faithfulness_delta": advanced.avg_faithfulness - baseline.avg_faithfulness,
                "relevancy_delta": advanced.avg_answer_relevancy - baseline.avg_answer_relevancy,
                "precision_delta": advanced.avg_context_precision - baseline.avg_context_precision,
            },
        }

        logger.info("📈 Comparison Results:")
        logger.info(
            f"  Baseline: similarity={baseline.avg_similarity:.3f}, "
            f"faithfulness={baseline.avg_faithfulness:.3f}, "
            f"relevancy={baseline.avg_answer_relevancy:.3f}"
        )
        logger.info(
            f"  Advanced: similarity={advanced.avg_similarity:.3f}, "
            f"faithfulness={advanced.avg_faithfulness:.3f}, "
            f"relevancy={advanced.avg_answer_relevancy:.3f}"
        )

        return comparison

    def print_report(self, report: BatchEvaluationReport) -> None:
        """
        打印评估报告

        Args:
            report: 批量评估报告
        """
        print("\n" + "=" * 80)
        print("📊 RAG 评估报告 (基于 RAGAS)")
        print("=" * 80)
        print(f"总测试用例数: {report.total_queries}")
        print()
        print("🔍 检索指标:")
        print(f"  平均相似度: {report.avg_similarity:.3f}")
        print(f"  平均检索延迟: {report.avg_retrieval_latency:.1f}ms")
        print()
        print("🎯 生成质量指标 (RAGAS):")
        if report.avg_faithfulness > 0:
            print(f"  忠实度 (Faithfulness): {report.avg_faithfulness:.3f}")
        if report.avg_answer_relevancy > 0:
            print(f"  答案相关性 (Answer Relevancy): {report.avg_answer_relevancy:.3f}")
        if report.avg_context_precision > 0:
            print(f"  上下文精确度 (Context Precision): {report.avg_context_precision:.3f}")
        if report.avg_context_recall > 0:
            print(f"  上下文召回率 (Context Recall): {report.avg_context_recall:.3f}")
        if report.avg_answer_correctness > 0:
            print(f"  答案正确性 (Answer Correctness): {report.avg_answer_correctness:.3f}")
        print("=" * 80)
