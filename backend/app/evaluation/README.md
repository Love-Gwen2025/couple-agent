# RAG 评估系统 - 基于 RAGAS 框架

本目录包含基于 RAGAS 框架的科学化 RAG 评估工具。

## 文件说明

| 文件 | 说明 |
|------|------|
| `rag_evaluator.py` | 评估器，集成 RAGAS 标准指标 |
| `dataset_generator.py` | 数据集生成器，支持 Ground Truth |

## 功能特性

1. **集成 RAGAS 框架** - 支持业界标准评估指标
2. **生成质量评估** - 评估忠实度、答案相关性等
3. **Ground Truth 支持** - 可选的标准答案和上下文
4. **端到端评估** - 评估完整的检索+生成流程

## RAGAS 评估指标

| 指标 | 说明 | 取值范围 | 需要 Ground Truth |
|------|------|----------|------------------|
| **Faithfulness** | 生成答案对检索上下文的忠实度 | 0-1 | 否 |
| **Answer Relevancy** | 答案与问题的相关性 | 0-1 | 否 |
| **Context Precision** | 检索上下文的精确度 | 0-1 | 否 |
| **Context Recall** | 检索上下文的召回率 | 0-1 | 是 |
| **Answer Correctness** | 答案的正确性 | 0-1 | 是 |

## 快速开始

### 方法1：快速测试（推荐新手）

测试几个查询，快速了解评估结果：

```bash
cd backend

# 1. 编辑 scripts/quick_rag_eval.py，配置你的知识库 ID 和测试查询
# 2. 运行快速评估（方式1：使用 -m 模式）
uv run python -m scripts.quick_rag_eval

# 或方式2：直接运行
uv run python scripts/quick_rag_eval.py
```

输出示例：
```
查询 1/3: 什么是向量数据库？
================================================================================

评估结果:
  检索结果数: 5
  平均相似度: 0.845
  检索延迟: 42.3ms

RAGAS 质量指标:
  忠实度 (Faithfulness): 0.923
  答案相关性 (Answer Relevancy): 0.887
  上下文精确度 (Context Precision): 0.756

总延迟: 1234.5ms

质量评价:
  生成的答案忠实于检索内容
  答案与问题高度相关
```

### 方法2：完整评估流程

生成数据集 + 批量评估 + 方法对比：

```bash
cd backend

# 完整评估（自动生成数据集 + 评估 + 对比）
uv run python -m scripts.run_rag_eval_v2 \
  --kb-ids 1,2 \
  --sample-size 20 \
  --questions-per-chunk 2

# 使用已有数据集
uv run python -m scripts.run_rag_eval_v2 \
  --kb-ids 1,2 \
  --dataset-file eval_results/dataset_20260121_120000.json

# 跳过方法对比（仅评估基础方法，更快）
uv run python -m scripts.run_rag_eval_v2 \
  --kb-ids 1,2 \
  --sample-size 10 \
  --skip-comparison
```

参数说明：
- `--kb-ids`: 知识库 ID，逗号分隔（必需）
- `--sample-size`: 抽样文档块数量（默认10）
- `--questions-per-chunk`: 每个块生成的问题数（默认2）
- `--dataset-file`: 使用已有数据集（跳过生成步骤）
- `--skip-comparison`: 跳过方法对比
- `--output-dir`: 输出目录（默认 `eval_results`）

### 方法3：代码集成

在你的代码中使用评估器：

```python
from app.evaluation.rag_evaluator import RAGEvaluator
from app.services.embedding_service import EmbeddingService
from app.core.db import SessionLocal
from langchain_openai import ChatOpenAI

# 初始化
embedding_service = EmbeddingService(settings)
model = ChatOpenAI(model="gpt-4o-mini")
evaluator = RAGEvaluator(embedding_service, model)

# 评估单个查询
async with SessionLocal() as db:
    metrics = await evaluator.evaluate_rag_pipeline(
        db=db,
        query="什么是向量数据库？",
        knowledge_base_ids=[1, 2],
        use_advanced=False,  # True = 高级检索
        ground_truth_answer="向量数据库是...",  # 可选
    )

    print(f"忠实度: {metrics.faithfulness_score:.3f}")
    print(f"答案相关性: {metrics.answer_relevancy_score:.3f}")
```

## 输出文件

评估结果保存在 `eval_results/` 目录：

```
eval_results/
├── dataset_20260121_120000.json      # 生成的测试数据集
├── report_baseline_20260121_120530.json  # 基础方法评估报告
└── comparison_20260121_121045.json   # 方法对比结果
```

### 数据集格式

```json
{
  "metadata": {
    "generated_at": "2026-01-21T12:00:00",
    "total_cases": 20
  },
  "test_cases": [
    {
      "id": 1,
      "query": "什么是向量数据库？",
      "ground_truth_answer": "向量数据库是专门用于...",
      "relevant_chunk_ids": [123],
      "relevant_contexts": ["文档内容..."],
      "knowledge_base_ids": [1],
      "difficulty": "medium"
    }
  ]
}
```

### 评估报告格式

```json
{
  "metadata": {
    "generated_at": "2026-01-21T12:05:30",
    "total_queries": 20
  },
  "summary": {
    "avg_similarity": 0.823,
    "avg_faithfulness": 0.887,
    "avg_answer_relevancy": 0.856,
    "avg_context_precision": 0.734
  },
  "details": [...]
}
```

## 高级用法

### 1. 生成带 Ground Truth 的数据集

```python
from app.evaluation.dataset_generator import DatasetGenerator

generator = DatasetGenerator(model=model)

async with SessionLocal() as db:
    dataset = await generator.generate_dataset(
        db=db,
        knowledge_base_ids=[1, 2],
        sample_size=50,
        questions_per_chunk=2,
        generate_answer=True,  # 生成标准答案
    )

    generator.save_dataset(dataset, "my_dataset.json")
```

### 2. 批量评估

```python
test_cases = [
    {
        "query": "什么是向量数据库？",
        "knowledge_base_ids": [1, 2],
        "ground_truth_answer": "向量数据库是...",  # 可选
        "ground_truth_contexts": ["相关文档..."],  # 可选
    },
    # 更多测试用例...
]

report = await evaluator.evaluate_batch(
    db=db,
    test_cases=test_cases,
    use_advanced=False,
)

evaluator.print_report(report)
```

### 3. 对比基础 vs 高级方法

```python
comparison = await evaluator.compare_methods(
    db=db,
    test_cases=test_cases,
)

print(comparison["improvement"]["faithfulness_delta"])  # 忠实度改进幅度
```

## 使用建议

### 评估频率

- **开发阶段**：每次重大修改后评估一次
- **迭代优化**：每周评估一次，跟踪改进趋势
- **生产监控**：每天自动评估固定测试集

### 数据集规模

- **快速验证**：5-10 个测试用例
- **日常评估**：20-50 个测试用例
- **全面评估**：100+ 个测试用例

### Ground Truth 策略

**有 Ground Truth**：
- 更准确的评估
- 可计算 Context Recall 和 Answer Correctness
- 需要人工标注或 LLM 生成

**无 Ground Truth**：
- 快速评估，无需标注
- 仍可评估 Faithfulness、Answer Relevancy、Context Precision
- 无法评估召回率和绝对正确性

**推荐**：
1. 核心场景用例：使用 Ground Truth
2. 日常评估：无 Ground Truth（快速迭代）
3. 定期验证：人工审查部分结果，校准评估标准

## 常见问题

### Q: RAGAS 评估很慢怎么办？

A: RAGAS 需要调用 LLM 进行评估，有几个优化方法：
1. 使用更快的模型（如 `gpt-4o-mini` 而非 `gpt-4o`）
2. 减少测试用例数量
3. 设置 `--skip-comparison` 只评估一种方法
4. 使用缓存的数据集（`--dataset-file`）避免重复生成

### Q: 如何理解 Faithfulness 分数？

A: Faithfulness（忠实度）评估生成的答案是否忠于检索到的上下文：
- **0.9-1.0**：答案完全基于上下文，无幻觉
- **0.7-0.9**：大部分内容基于上下文，少量推理
- **< 0.7**：存在明显的幻觉或不实陈述

### Q: 没有 Ground Truth 能用吗？

A: 可以！RAGAS 的核心指标（Faithfulness、Answer Relevancy、Context Precision）不需要 Ground Truth。只有 Context Recall 和 Answer Correctness 需要。

### Q: 如何获取 Ground Truth？

A: 三种方式：
1. **自动生成**（本项目支持）：使用 LLM 从文档生成问答对
2. **人工标注**：专家标注标准答案
3. **混合方式**：LLM 生成 + 人工审核

## 相关资源

- [RAGAS 官方文档](https://docs.ragas.io/)
- [RAGAS GitHub](https://github.com/explodinggradients/ragas)
- [RAG 评估最佳实践](https://www.chatbench.org/ragas-framework-for-rag-evaluation/)
