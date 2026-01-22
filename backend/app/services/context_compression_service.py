"""
上下文压缩服务（Context Compression）

对检索到的文档片段进行压缩，只保留与查询相关的关键信息，
避免将过多无关内容注入到 LLM 上下文中。

优势：
1. 减少 Token 消耗
2. 降低噪音干扰
3. 提高回答质量
"""

from loguru import logger

# 上下文压缩 Prompt
COMPRESSION_PROMPT = """你是一个文档压缩专家。你的任务是从文档片段中提取与用户问题相关的关键信息。

# 用户问题
{question}

# 文档片段
{content}

# 任务要求
1. 仔细阅读文档片段
2. 只提取与用户问题直接相关的信息
3. 删除冗余、重复、无关的内容
4. 保持信息的准确性和完整性
5. 如果文档与问题完全无关，输出"[无相关内容]"

# 压缩后的内容：
"""


class ContextCompressionService:
    """
    上下文压缩服务

    使用 LLM 对检索结果进行压缩，
    提取与用户问题相关的关键信息。
    """

    def __init__(self, model=None):
        """
        初始化上下文压缩服务

        Args:
            model: LLM 模型实例
        """
        self.model = model

    async def compress_chunk(self, question: str, content: str) -> str:
        """
        压缩单个文档片段

        Args:
            question: 用户问题
            content: 文档片段内容

        Returns:
            压缩后的内容
        """
        if not self.model:
            logger.warning("No model configured for compression, returning original content")
            return content

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            prompt = COMPRESSION_PROMPT.format(
                question=question,
                content=content,
            )

            response = await self.model.ainvoke(
                [
                    SystemMessage(content="你是一个文档压缩专家。"),
                    HumanMessage(content=prompt),
                ]
            )

            compressed = response.content.strip()

            # 检查是否无相关内容
            if "[无相关内容]" in compressed:
                return ""

            return compressed

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return content  # 失败时返回原内容

    async def compress_chunks(
        self,
        question: str,
        chunks: list[dict],
        content_key: str = "content",
        max_parallel: int = 5,
    ) -> list[dict]:
        """
        批量压缩多个文档片段

        Args:
            question: 用户问题
            chunks: 文档片段列表
            content_key: 内容字段名
            max_parallel: 最大并行数

        Returns:
            压缩后的文档片段列表（过滤掉无关内容）
        """
        import asyncio

        if not chunks:
            return []

        # 限制并行数量，避免过载
        semaphore = asyncio.Semaphore(max_parallel)

        async def compress_with_limit(chunk: dict) -> dict | None:
            async with semaphore:
                original_content = chunk.get(content_key, "")
                compressed_content = await self.compress_chunk(question, original_content)

                if not compressed_content:
                    return None  # 无关内容，跳过

                # 创建新的 chunk，更新 content
                result = dict(chunk)
                result[content_key] = compressed_content
                result["original_length"] = len(original_content)
                result["compressed_length"] = len(compressed_content)
                result["compression_ratio"] = (
                    len(compressed_content) / len(original_content) if original_content else 0
                )
                return result

        # 并行压缩
        results = await asyncio.gather(*[compress_with_limit(c) for c in chunks])

        # 过滤掉 None 结果
        compressed_chunks = [r for r in results if r is not None]

        # 统计
        original_total = sum(len(c.get(content_key, "")) for c in chunks)
        compressed_total = sum(len(c.get(content_key, "")) for c in compressed_chunks)
        ratio = compressed_total / original_total if original_total > 0 else 0

        logger.info(
            f"📦 Context compression: {len(chunks)} chunks -> {len(compressed_chunks)} chunks, "
            f"size: {original_total} -> {compressed_total} chars ({ratio:.1%})"
        )

        return compressed_chunks

    async def compress_context_string(
        self,
        question: str,
        context: str,
        max_length: int = 2000,
    ) -> str:
        """
        压缩整个上下文字符串

        Args:
            question: 用户问题
            context: 完整上下文
            max_length: 压缩后最大长度

        Returns:
            压缩后的上下文
        """
        if len(context) <= max_length:
            return context

        # 先尝试用 LLM 压缩
        compressed = await self.compress_chunk(question, context)

        # 如果还是太长，截断
        if len(compressed) > max_length:
            compressed = compressed[:max_length] + "..."

        return compressed
