"""
Query Rewriting 服务（查询改写）

将用户的原始查询改写为多个检索友好的查询变体，提高 RAG 召回率。

改写策略：
1. 同义词扩展 - 使用不同表述方式
2. 子问题分解 - 将复杂问题拆解
3. 上下文补全 - 补充隐含信息
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

# 解析响应（使用通用工具函数处理 Gemini 等模型的列表格式）
from app.utils.content import extract_text_content

# 查询改写 Prompt
QUERY_REWRITE_PROMPT = """你是一个专业的查询改写专家。你的任务是将用户的原始问题改写为多个适合向量检索的查询变体。

# 改写原则
1. 保持原始问题的核心意图
2. 使用不同的表述方式（同义词替换）
3. 如果问题复杂，可以拆解为子问题
4. 补充可能隐含的上下文信息
5. 每个改写查询应该独立、完整、无歧义

# 原始问题
{question}

# 对话上下文（可选）
{context}

# 输出要求
- 输出 3 个改写后的查询
- 每个查询单独一行
- 不要输出序号或其他格式

# 改写查询：
"""


class QueryRewriteService:
    """
    查询改写服务

    使用 LLM 将用户查询改写为多个检索友好的变体，
    然后对所有变体进行检索并合并结果。
    """

    def __init__(self, model: ChatOpenAI | None = None):
        """
        初始化查询改写服务

        Args:
            model: 可选的 LLM 模型，用于查询改写
        """
        self.model = model

    async def rewrite_query(
        self,
        question: str,
        context: str = "",
        num_rewrites: int = 3,
    ) -> list[str]:
        """
        将原始查询改写为多个检索友好的变体

        Args:
            question: 用户原始问题
            context: 可选的对话上下文
            num_rewrites: 生成的改写数量

        Returns:
            改写后的查询列表（包含原始查询）
        """
        # 总是包含原始查询
        queries = [question]

        # 如果没有配置模型，仅返回原始查询
        if not self.model:
            logger.warning("No model configured for query rewriting, using original query only")
            return queries

        try:
            # 构建改写 Prompt
            prompt = QUERY_REWRITE_PROMPT.format(
                question=question,
                context=context if context else "无",
            )

            # 调用 LLM 进行改写
            response = await self.model.ainvoke(
                [
                    SystemMessage(content="你是一个专业的查询改写专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            content_str = extract_text_content(response.content)
            rewritten_lines = content_str.strip().split("\n")
            for line in rewritten_lines:
                line = line.strip()
                # 过滤空行和重复
                if line and line != question and line not in queries:
                    queries.append(line)
                    if len(queries) >= num_rewrites + 1:  # +1 包含原始查询
                        break

            logger.info(
                f"🔄 Query rewriting: original='{question[:30]}...' -> {len(queries)} variants"
            )
            for i, q in enumerate(queries):
                logger.debug(f"  [{i}] {q[:50]}...")

            return queries

        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return queries  # 失败时返回原始查询

    async def expand_and_merge_search(
        self,
        question: str,
        search_func,
        context: str = "",
        **search_kwargs,
    ) -> list[dict]:
        """
        改写查询并合并多个查询的检索结果

        Args:
            question: 用户原始问题
            search_func: 检索函数（async），接受 query 参数
            context: 可选的对话上下文
            **search_kwargs: 传递给 search_func 的其他参数

        Returns:
            去重合并后的检索结果列表
        """
        import asyncio

        # 1. 改写查询
        queries = await self.rewrite_query(question, context)

        # 2. 并行执行多个查询
        async def search_with_query(query: str):
            return await search_func(query=query, **search_kwargs)

        results_list = await asyncio.gather(*[search_with_query(q) for q in queries])

        # 3. 合并去重（基于 document_id + chunk_index）
        seen_keys = set()
        merged_results = []

        for results in results_list:
            for item in results:
                # 生成唯一键
                key = f"{item.get('document_id', '')}_{item.get('chunk_index', '')}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    merged_results.append(item)

        logger.info(
            f"🔄 Query expansion: {len(queries)} queries -> {sum(len(r) for r in results_list)} results -> "
            f"{len(merged_results)} after dedup"
        )

        return merged_results
