"""
RAG 评估数据集生成器

从知识库自动生成评估数据集，用于 RAG 系统的离线评估。

使用方法：
    python -m app.evaluation.dataset_generator --kb-id 1 --output test_dataset.json
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker
from app.models.knowledge import KnowledgeChunk


class DatasetGenerator:
    """评估数据集生成器"""

    def __init__(self, model: ChatOpenAI):
        """
        初始化生成器

        Args:
            model: 用于生成问题的 LLM 模型
        """
        self.model = model

    async def generate_questions_from_chunk(
        self,
        chunk_content: str,
        chunk_file_name: str,
        num_questions: int = 2,
        generate_answer: bool = True,
    ) -> list[dict]:
        """
        根据文档块内容生成问题（并可选生成答案作为 Ground Truth）

        Args:
            chunk_content: 文档块内容
            chunk_file_name: 来源文件名
            num_questions: 生成问题数量
            generate_answer: 是否生成标准答案

        Returns:
            问题列表，每个元素为 {"question": str, "ground_truth_answer": str}
        """
        if generate_answer:
            prompt = f"""你是一个问答数据生成专家。根据以下文档内容，生成 {num_questions} 个问答对。

要求：
1. 问题要自然，像真实用户会问的
2. 问题难度适中，需要参考文档才能回答
3. 答案要准确，完全基于文档内容
4. 格式：Q: 问题\nA: 答案\n

文档来源：{chunk_file_name}
文档内容：
{chunk_content[:2000]}

请生成 {num_questions} 个问答对："""
        else:
            prompt = f"""你是一个问题生成专家。根据以下文档内容，生成 {num_questions} 个用户可能会问的问题。

要求：
1. 问题要自然，像真实用户会问的
2. 问题难度适中，需要参考文档才能回答
3. 每个问题一行，不要编号

文档来源：{chunk_file_name}
文档内容：
{chunk_content[:2000]}

请生成 {num_questions} 个问题："""

        try:
            response = await self.model.ainvoke(prompt)
            content = response.content.strip()

            if generate_answer:
                # 解析 Q&A 格式
                qa_pairs = []
                lines = content.split("\n")
                current_q = None
                current_a = None

                for line in lines:
                    line = line.strip()
                    if line.startswith("Q:") or line.startswith("问题:"):
                        if current_q and current_a:
                            qa_pairs.append(
                                {"question": current_q, "ground_truth_answer": current_a}
                            )
                        current_q = line.split(":", 1)[1].strip()
                        current_a = None
                    elif line.startswith("A:") or line.startswith("答案:"):
                        current_a = line.split(":", 1)[1].strip()

                # 添加最后一对
                if current_q and current_a:
                    qa_pairs.append({"question": current_q, "ground_truth_answer": current_a})

                return qa_pairs[:num_questions]
            else:
                # 只返回问题
                questions = [q.strip() for q in content.split("\n") if q.strip()]
                return [{"question": q, "ground_truth_answer": None} for q in questions][
                    :num_questions
                ]

        except Exception as e:
            logger.warning(f"生成问题失败: {e}")
            return []

    async def generate_dataset(
        self,
        db: AsyncSession,
        knowledge_base_ids: list[int],
        sample_size: int = 50,
        questions_per_chunk: int = 2,
        generate_answer: bool = True,
    ) -> list[dict]:
        """
        生成评估数据集

        Args:
            db: 数据库会话
            knowledge_base_ids: 知识库 ID 列表
            sample_size: 抽样的文档块数量
            questions_per_chunk: 每个块生成的问题数
            generate_answer: 是否生成标准答案（Ground Truth）

        Returns:
            评估数据集
        """
        logger.info(
            f"🚀 开始生成数据集: kb_ids={knowledge_base_ids}, sample_size={sample_size}, "
            f"generate_answer={generate_answer}"
        )

        # 1. 获取知识库中的文档块总数
        count_query = select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.knowledge_base_id.in_(knowledge_base_ids)
        )
        total_count = await db.scalar(count_query)
        logger.info(f"📊 知识库共有 {total_count} 个文档块")

        if total_count == 0:
            logger.warning("知识库为空，无法生成数据集")
            return []

        # 2. 随机抽样文档块
        # 使用 RANDOM() 进行随机排序
        sample_query = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.knowledge_base_id.in_(knowledge_base_ids))
            .order_by(func.random())
            .limit(sample_size)
        )
        result = await db.execute(sample_query)
        chunks = result.scalars().all()
        logger.info(f"📝 已抽样 {len(chunks)} 个文档块")

        # 3. 为每个块生成问题
        dataset = []
        for i, chunk in enumerate(chunks):
            logger.info(f"⏳ 处理文档块 {i + 1}/{len(chunks)}: {chunk.file_name}")

            qa_pairs = await self.generate_questions_from_chunk(
                chunk_content=chunk.content,
                chunk_file_name=chunk.file_name,
                num_questions=questions_per_chunk,
                generate_answer=generate_answer,
            )

            for qa in qa_pairs:
                dataset.append(
                    {
                        "id": len(dataset) + 1,
                        "query": qa["question"],
                        "ground_truth_answer": qa.get("ground_truth_answer"),
                        "relevant_chunk_ids": [chunk.id],
                        "relevant_contexts": [chunk.content],  # 新增：Ground Truth 上下文
                        "relevant_document_id": chunk.document_id,
                        "source_file": chunk.file_name,
                        "knowledge_base_ids": [chunk.knowledge_base_id],
                        "difficulty": self._estimate_difficulty(qa["question"], chunk.content),
                    }
                )

            # 避免 API 限流
            await asyncio.sleep(0.5)

        logger.info(f"✅ 数据集生成完成，共 {len(dataset)} 个测试用例")
        return dataset

    def _estimate_difficulty(self, question: str, content: str) -> str:
        """
        估算问题难度

        Args:
            question: 问题
            content: 相关文档内容

        Returns:
            难度级别: easy/medium/hard
        """
        # 简单的启发式规则
        question_len = len(question)
        content_len = len(content)

        if question_len < 20:
            return "easy"
        elif question_len > 50 or content_len > 1000:
            return "hard"
        else:
            return "medium"

    def save_dataset(self, dataset: list[dict], output_path: str) -> None:
        """
        保存数据集到文件

        Args:
            dataset: 数据集
            output_path: 输出文件路径
        """
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_cases": len(dataset),
                "difficulty_distribution": {
                    "easy": len([d for d in dataset if d["difficulty"] == "easy"]),
                    "medium": len([d for d in dataset if d["difficulty"] == "medium"]),
                    "hard": len([d for d in dataset if d["difficulty"] == "hard"]),
                },
            },
            "test_cases": dataset,
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 数据集已保存到: {output_path}")


async def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG 评估数据集生成器")
    parser.add_argument("--kb-ids", type=str, required=True, help="知识库 ID，逗号分隔")
    parser.add_argument("--sample-size", type=int, default=50, help="抽样文档块数量")
    parser.add_argument("--questions-per-chunk", type=int, default=2, help="每个块生成的问题数")
    parser.add_argument("--output", type=str, default="test_dataset.json", help="输出文件路径")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="用于生成问题的模型")
    parser.add_argument("--api-key", type=str, help="OpenAI API Key")
    parser.add_argument("--base-url", type=str, help="OpenAI API Base URL")

    args = parser.parse_args()

    # 解析知识库 ID
    kb_ids = [int(x.strip()) for x in args.kb_ids.split(",")]

    # 创建模型
    model_kwargs = {"model": args.model}
    if args.api_key:
        model_kwargs["api_key"] = args.api_key
    if args.base_url:
        model_kwargs["base_url"] = args.base_url

    model = ChatOpenAI(**model_kwargs)

    # 生成数据集
    generator = DatasetGenerator(model=model)

    async with async_session_maker() as db:
        dataset = await generator.generate_dataset(
            db=db,
            knowledge_base_ids=kb_ids,
            sample_size=args.sample_size,
            questions_per_chunk=args.questions_per_chunk,
        )

    # 保存数据集
    generator.save_dataset(dataset, args.output)


if __name__ == "__main__":
    asyncio.run(main())
