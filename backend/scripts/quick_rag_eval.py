"""
RAG 评估快速示例（基于 RAGAS）

快速测试几个查询的 RAG 质量，不需要生成完整数据集。

使用方法：
    cd backend
    uv run python -m scripts.quick_rag_eval
"""

import asyncio
import sys
from pathlib import Path

from loguru import logger  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.evaluation.rag_evaluator import RAGEvaluator  # noqa: E402
from app.services.embedding_service import EmbeddingService

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# ========== 测试查询配置 ==========
# 修改这里的配置以测试你的知识库
KNOWLEDGE_BASE_IDS = [272547608658972672]  # 你的知识库 ID

TEST_QUERIES = [
    {
        "query": "土巴兔一面的问题",
        # 可选：提供 Ground Truth 用于更准确的评估
        # "ground_truth_answer": "向量数据库是专门用于存储和检索向量 embeddings 的数据库...",
    }
]


async def main():
    """快速评估示例"""
    logger.info("🚀 开始 RAG 快速评估")

    # 1. 初始化服务
    settings = get_settings()
    embedding_service = EmbeddingService(settings)

    # 2. 创建 LLM 模型（用于 RAGAS 评估）
    # 注意：RAGAS 需要能正确输出结构化 JSON 的模型
    # 使用 Gemini 官方 API（RAGAS 完全支持）

    from langchain_google_genai import ChatGoogleGenerativeAI


    model = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",  # RAGAS 推荐模型，也可用 gemini-3-flash-preview
        google_api_key="AIzaSyBNPkrzf7vg7O2v1iSS42jlCDq4H0DttJI",
        temperature=0,  # 评估时建议使用低温度以保证一致性
    )
    logger.info("使用 Gemini 进行 RAGAS 评估")

    # 3. 创建评估器
    evaluator = RAGEvaluator(embedding_service=embedding_service, model=model)

    # 4. 逐个评估测试查询
    async with SessionLocal() as db:
        logger.info(f"📊 评估 {len(TEST_QUERIES)} 个测试查询\n")

        for i, test_case in enumerate(TEST_QUERIES, 1):
            query = test_case["query"]
            ground_truth = test_case.get("ground_truth_answer")

            print(f"\n{'=' * 80}")
            print(f"查询 {i}/{len(TEST_QUERIES)}: {query}")
            print("=" * 80)

            # 评估该查询
            metrics = await evaluator.evaluate_rag_pipeline(
                db=db,
                query=query,
                knowledge_base_ids=KNOWLEDGE_BASE_IDS,
                use_advanced=False,  # 改为 True 使用高级检索
                ground_truth_answer=ground_truth,
            )

            # 打印结果
            print("\n📈 评估结果:")
            print(f"  检索结果数: {metrics.num_retrieved}")
            print(f"  平均相似度: {metrics.avg_similarity:.3f}")
            print(f"  检索延迟: {metrics.retrieval_latency_ms:.1f}ms")

            # 检查是否有有效的 RAGAS 评估结果（排除 nan 和 None）
            import math

            has_valid_faithfulness = metrics.faithfulness_score is not None and not (
                isinstance(metrics.faithfulness_score, float)
                and math.isnan(metrics.faithfulness_score)
            )
            has_valid_relevancy = metrics.answer_relevancy_score is not None and not (
                isinstance(metrics.answer_relevancy_score, float)
                and math.isnan(metrics.answer_relevancy_score)
            )

            if has_valid_faithfulness or has_valid_relevancy:
                print("\n🎯 RAGAS 质量指标:")
                if has_valid_faithfulness:
                    print(f"  忠实度 (Faithfulness): {metrics.faithfulness_score:.3f}")
                if has_valid_relevancy:
                    print(f"  答案相关性 (Answer Relevancy): {metrics.answer_relevancy_score:.3f}")
                if metrics.context_precision_score is not None:
                    print(
                        f"  上下文精确度 (Context Precision): {metrics.context_precision_score:.3f}"
                    )

                if metrics.answer_correctness_score:
                    print(
                        f"  答案正确性 (Answer Correctness): {metrics.answer_correctness_score:.3f}"
                    )
            else:
                print("\n⚠️  RAGAS 评估返回 nan，可能是 LLM 响应格式问题")

            print(f"\n⏱️  总延迟: {metrics.total_latency_ms:.1f}ms")

            # 简单的质量判断
            print("\n💡 质量评价:")
            if metrics.faithfulness_score and metrics.faithfulness_score > 0.8:
                print("  ✅ 生成的答案忠实于检索内容")
            elif metrics.faithfulness_score and metrics.faithfulness_score < 0.6:
                print("  ⚠️  生成的答案可能存在幻觉")

            if metrics.answer_relevancy_score and metrics.answer_relevancy_score > 0.8:
                print("  ✅ 答案与问题高度相关")
            elif metrics.answer_relevancy_score and metrics.answer_relevancy_score < 0.6:
                print("  ⚠️  答案可能偏离了问题")

            print()

    logger.info("✅ 快速评估完成！")

    print("\n" + "=" * 80)
    print("💡 下一步:")
    print("  1. 调整 KNOWLEDGE_BASE_IDS 和 TEST_QUERIES 测试你的知识库")
    print("  2. 设置 use_advanced=True 对比高级检索效果")
    print("  3. 添加 ground_truth_answer 获取更准确的评估")
    print("  4. 使用 run_rag_eval_v2.py 进行完整的批量评估")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
