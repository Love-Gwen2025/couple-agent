"""
RAG 评估示例脚本（基于 RAGAS）

使用方法：
    cd backend
    uv run python -m scripts.run_rag_eval_v2 --kb-ids 1,2 --sample-size 10

完整工作流：
    1. 生成包含 Ground Truth 的评估数据集
    2. 使用 RAGAS 评估 RAG 系统质量
    3. 对比基础方法 vs 高级方法
    4. 输出详细报告
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from loguru import logger

from app.core.db import SessionLocal
from app.core.settings import get_settings
from app.evaluation.dataset_generator import DatasetGenerator
from app.evaluation.rag_evaluator import RAGEvaluator
from app.services.embedding_service import EmbeddingService

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))




async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RAG 评估脚本（基于 RAGAS）")
    parser.add_argument("--kb-ids", type=str, required=True, help="知识库 ID，逗号分隔")
    parser.add_argument("--sample-size", type=int, default=10, help="抽样文档块数量")
    parser.add_argument("--questions-per-chunk", type=int, default=2, help="每个块生成的问题数")
    parser.add_argument(
        "--dataset-file", type=str, default=None, help="使用已有数据集文件（跳过生成步骤）"
    )
    parser.add_argument("--output-dir", type=str, default="eval_results", help="输出目录")
    parser.add_argument(
        "--skip-comparison", action="store_true", help="跳过方法对比（仅评估基础方法）"
    )
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="用于生成和评估的模型")

    args = parser.parse_args()

    # 解析知识库 ID
    kb_ids = [int(x.strip()) for x in args.kb_ids.split(",")]

    # 初始化服务
    settings = get_settings()
    embedding_service = EmbeddingService(settings)

    # 创建 LLM 模型
    model = ChatOpenAI(
        model=args.model,
        api_key=settings.ai_deepseek_api_key,
        base_url=settings.ai_deepseek_base_url,
    )

    logger.info("🚀开始RAG评估流程")
    logger.info(f"📚 知识库 ID: {kb_ids}")
    logger.info(f"🤖 使用模型: {args.model}")

    # ========== 步骤 1: 生成或加载数据集 ==========
    if args.dataset_file:
        logger.info(f"📂 加载已有数据集: {args.dataset_file}")
        with open(args.dataset_file, encoding="utf-8") as f:
            data = json.load(f)
            dataset = data.get("test_cases", [])
    else:
        logger.info("🔨 生成评估数据集（包含 Ground Truth）")
        generator = DatasetGenerator(model=model)

        async with SessionLocal() as db:
            dataset = await generator.generate_dataset(
                db=db,
                knowledge_base_ids=kb_ids,
                sample_size=args.sample_size,
                questions_per_chunk=args.questions_per_chunk,
                generate_answer=True,  # 生成标准答案
            )

        # 保存数据集
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_file = f"{args.output_dir}/dataset_{timestamp}.json"
        generator.save_dataset(dataset, dataset_file)
        logger.info(f"💾 数据集已保存: {dataset_file}")

    if not dataset:
        logger.error("❌ 数据集为空，无法继续评估")
        return

    # 转换数据集格式为评估器所需格式
    test_cases = [
        {
            "query": case["query"],
            "knowledge_base_ids": case.get("knowledge_base_ids", kb_ids),
            "ground_truth_answer": case.get("ground_truth_answer"),
            "ground_truth_contexts": case.get("relevant_contexts"),
        }
        for case in dataset
    ]

    logger.info(f"📊 数据集大小: {len(test_cases)} 个测试用例")

    # ========== 步骤 2: 创建评估器 ==========
    evaluator = RAGEvaluator(embedding_service=embedding_service, model=model)

    # ========== 步骤 3: 执行评估 ==========
    async with SessionLocal() as db:
        if args.skip_comparison:
            # 仅评估基础方法
            logger.info("🔍 评估基础检索方法（混合检索）")
            report = await evaluator.evaluate_batch(
                db=db, test_cases=test_cases, use_advanced=False
            )

            # 打印报告
            evaluator.print_report(report)

            # 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"{args.output_dir}/report_baseline_{timestamp}.json"
            save_report(report, report_file)
            logger.info(f"💾 评估报告已保存: {report_file}")

        else:
            # 对比基础 vs 高级方法
            logger.info("📈 对比基础方法 vs 高级方法")
            comparison = await evaluator.compare_methods(db=db, test_cases=test_cases)

            # 打印对比结果
            print_comparison(comparison)

            # 保存对比结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            comparison_file = f"{args.output_dir}/comparison_{timestamp}.json"
            with open(comparison_file, "w", encoding="utf-8") as f:
                json.dump(comparison, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 对比结果已保存: {comparison_file}")

    logger.info("✅ RAG 评估完成！")


def save_report(report, output_path: str) -> None:
    """保存评估报告为 JSON"""
    from pathlib import Path

    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_queries": report.total_queries,
        },
        "summary": {
            "avg_retrieval_latency": report.avg_retrieval_latency,
            "avg_similarity": report.avg_similarity,
            "avg_faithfulness": report.avg_faithfulness,
            "avg_answer_relevancy": report.avg_answer_relevancy,
            "avg_context_precision": report.avg_context_precision,
            "avg_context_recall": report.avg_context_recall,
            "avg_answer_correctness": report.avg_answer_correctness,
        },
        "details": [
            {
                "query": m.query,
                "num_retrieved": m.num_retrieved,
                "retrieval_latency_ms": m.retrieval_latency_ms,
                "avg_similarity": m.avg_similarity,
                "faithfulness": m.faithfulness_score,
                "answer_relevancy": m.answer_relevancy_score,
                "context_precision": m.context_precision_score,
                "context_recall": m.context_recall_score,
                "answer_correctness": m.answer_correctness_score,
                "total_latency_ms": m.total_latency_ms,
            }
            for m in report.metrics_list
        ],
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def print_comparison(comparison: dict) -> None:
    """打印对比结果"""
    print("\n" + "=" * 80)
    print("📊 基础方法 vs 高级方法对比")
    print("=" * 80)

    baseline = comparison["baseline"]
    advanced = comparison["advanced"]
    improvement = comparison["improvement"]

    print("\n🔵 基础方法（混合检索）:")
    print(f"  相似度: {baseline['avg_similarity']:.3f}")
    print(f"  检索延迟: {baseline['avg_retrieval_latency']:.1f}ms")
    print(f"  忠实度: {baseline['avg_faithfulness']:.3f}")
    print(f"  答案相关性: {baseline['avg_answer_relevancy']:.3f}")
    print(f"  上下文精确度: {baseline['avg_context_precision']:.3f}")

    print("\n🟢 高级方法（查询重写 + 重排序）:")
    print(f"  相似度: {advanced['avg_similarity']:.3f}")
    print(f"  检索延迟: {advanced['avg_retrieval_latency']:.1f}ms")
    print(f"  忠实度: {advanced['avg_faithfulness']:.3f}")
    print(f"  答案相关性: {advanced['avg_answer_relevancy']:.3f}")
    print(f"  上下文精确度: {advanced['avg_context_precision']:.3f}")

    print("\n📈 改进幅度:")
    print(f"  相似度: {improvement['similarity_delta']:+.3f}")
    print(f"  延迟变化: {improvement['latency_delta']:+.1f}ms")
    print(f"  忠实度: {improvement['faithfulness_delta']:+.3f}")
    print(f"  答案相关性: {improvement['relevancy_delta']:+.3f}")
    print(f"  上下文精确度: {improvement['precision_delta']:+.3f}")

    print("\n💡 建议:")
    if improvement["faithfulness_delta"] > 0.05:
        print("  ✅ 高级方法显著提升了生成的忠实度")
    if improvement["relevancy_delta"] > 0.05:
        print("  ✅ 高级方法显著提升了答案相关性")
    if improvement["latency_delta"] > 100:
        print("  ⚠️  高级方法增加了延迟，请权衡速度与质量")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
