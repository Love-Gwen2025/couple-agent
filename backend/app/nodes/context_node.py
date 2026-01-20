"""
上下文增强节点 (Context Augmentation Node)

Chat Mode 的并行检索层，负责：
1. 获取历史对话上下文（通过 RAG 检索相关历史）
2. 获取知识库上下文（通过向量检索相关文档）

两个检索并行执行，结果合并到 state 中供 chatbot 使用。
"""

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage
from loguru import logger

from app.utils.content import extract_text_content


async def get_history_context(
    query: str,
    embedding_service,
    db_session,
    conversation_id: int | None,
    top_k: int = 5,
    similarity_threshold: float = 0.6,
) -> str:
    """
    获取历史对话上下文

    Args:
        query: 用户查询
        embedding_service: Embedding 服务实例
        db_session: 数据库会话
        conversation_id: 会话 ID
        top_k: 返回结果数量
        similarity_threshold: 相似度阈值

    Returns:
        格式化的历史上下文字符串
    """
    if not embedding_service or not db_session or not conversation_id:
        return ""

    try:
        results = await embedding_service.search_similar(
            db=db_session,
            query=query,
            conversation_id=conversation_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if not results:
            return ""

        # 格式化结果
        formatted = []
        for i, msg in enumerate(results, 1):
            role = "用户" if msg["role"] == "user" else "助手"
            formatted.append(f"{i}. {role}: {msg['content']}")

        logger.info(f"📜 History context: found {len(results)} relevant messages")
        return "【相关历史对话】\n" + "\n".join(formatted)

    except Exception as e:
        logger.error(f"Failed to get history context: {e}")
        return ""


async def get_kb_context(
    query: str,
    embedding_service,
    db_session,
    knowledge_base_ids: list[int],
    top_k: int = 5,
    similarity_threshold: float = 0.5,
    use_hybrid: bool = True,
) -> str:
    """
    获取知识库上下文

    Args:
        query: 用户查询
        embedding_service: Embedding 服务实例
        db_session: 数据库会话
        knowledge_base_ids: 知识库 ID 列表
        top_k: 返回结果数量
        similarity_threshold: 相似度阈值
        use_hybrid: 是否使用混合检索（向量 + BM25）

    Returns:
        格式化的知识库上下文字符串
    """
    if not embedding_service or not db_session or not knowledge_base_ids:
        return ""

    try:
        if use_hybrid:
            results = await embedding_service.hybrid_search_knowledge_base(
                db=db_session,
                query=query,
                knowledge_base_ids=knowledge_base_ids,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                mode="union",
            )
        else:
            results = await embedding_service.search_knowledge_base(
                db=db_session,
                query=query,
                knowledge_base_ids=knowledge_base_ids,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

        if not results:
            return ""

        # 格式化结果
        formatted = []
        for i, chunk in enumerate(results, 1):
            source = chunk.get("file_name", "未知来源")
            content = chunk["content"]
            similarity = chunk.get("similarity", 0)
            formatted.append(f"{i}. [{source}] (相似度: {similarity:.2f})\n{content}")

        logger.info(f"📚 KB context: found {len(results)} relevant chunks")
        return "【知识库参考资料】\n" + "\n\n".join(formatted)

    except Exception as e:
        logger.error(f"Failed to get KB context: {e}")
        return ""


def create_context_node(settings):
    """
    创建上下文增强节点

    该节点并行执行历史检索和知识库检索，将结果合并到 state 中。

    Args:
        settings: 应用配置

    Returns:
        节点函数
    """

    async def context_node(state: dict[str, Any]) -> dict[str, Any]:
        """
        上下文增强节点：并行获取历史和知识库上下文

        输入 state:
          - messages: 消息列表
          - embedding_service: Embedding 服务（通过 config 注入）
          - db_session: 数据库会话（通过 config 注入）
          - conversation_id: 会话 ID（通过 config 注入）
          - knowledge_base_ids: 知识库 ID 列表

        输出 state:
          - history_context: 历史对话上下文
          - kb_context: 知识库上下文
        """
        messages = state.get("messages", [])

        # 从 state 中获取注入的依赖
        embedding_service = state.get("_embedding_service")
        db_session = state.get("_db_session")
        conversation_id = state.get("_conversation_id")
        knowledge_base_ids = state.get("knowledge_base_ids", [])

        # 提取用户查询
        query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                query = extract_text_content(msg.content)
                break

        if not query:
            logger.warning("No user query found for context retrieval")
            return {"history_context": "", "kb_context": ""}

        logger.info(f"🔍 Context retrieval for query: {query[:50]}...")

        # 并行执行两个检索任务
        history_task = get_history_context(
            query=query,
            embedding_service=embedding_service,
            db_session=db_session,
            conversation_id=conversation_id,
            top_k=settings.rag_top_k,
            similarity_threshold=settings.rag_similarity_threshold,
        )

        kb_task = get_kb_context(
            query=query,
            embedding_service=embedding_service,
            db_session=db_session,
            knowledge_base_ids=knowledge_base_ids,
            top_k=settings.rag_top_k,
            similarity_threshold=settings.rag_similarity_threshold,
            use_hybrid=True,
        )

        # 并行等待结果
        history_context, kb_context = await asyncio.gather(history_task, kb_task)

        logger.info(
            f"✅ Context retrieved: history={len(history_context)} chars, kb={len(kb_context)} chars"
        )

        return {
            "history_context": history_context,
            "kb_context": kb_context,
        }

    return context_node
