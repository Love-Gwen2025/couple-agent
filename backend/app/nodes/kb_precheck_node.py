"""
知识库预检查节点 (KB Pre-Check Node)

DeepSearch 模式的知识库预检查，负责：
1. 在 Planning 之前检索内部知识库
2. 将已知的内部知识注入到 references 中
3. 让 Planning 节点知道哪些信息已经有了，避免重复搜索

这样 DeepSearch 可以：
- 优先使用内部知识库的信息
- 只对知识库中没有的信息进行联网搜索
- 提高搜索效率和回答质量
"""

from typing import Any

from langchain_core.messages import HumanMessage
from loguru import logger

from app.utils.content import extract_text_content


def create_kb_precheck_node(settings):
    """
    创建知识库预检查节点

    Args:
        settings: 应用配置

    Returns:
        节点函数
    """

    async def kb_precheck_node(state: dict[str, Any]) -> dict[str, Any]:
        """
        知识库预检查节点：在 DeepSearch 规划前检索内部知识

        输入 state:
          - messages: 消息列表
          - question: 用户问题（可选，会自动从 messages 提取）
          - knowledge_base_ids: 知识库 ID 列表
          - _embedding_service: Embedding 服务（通过 config 注入）
          - _db_session: 数据库会话（通过 config 注入）

        输出 state:
          - references: 更新后的参考资料（注入内部知识）
          - question: 用户问题
          - kb_context: 知识库上下文（供后续节点使用）
        """
        messages = state.get("messages", [])
        question = state.get("question", "")
        references = state.get("references", {})
        knowledge_base_ids = state.get("knowledge_base_ids", [])

        # 从 state 中获取注入的依赖
        embedding_service = state.get("_embedding_service")
        db_session = state.get("_db_session")

        # 如果没有明确的 question，从最后一条用户消息提取
        if not question:
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    question = extract_text_content(msg.content)
                    break

        logger.info(f"🔎 KB Pre-Check for question: {question[:50]}...")

        # 如果没有配置知识库，直接返回
        if not knowledge_base_ids or not embedding_service or not db_session:
            logger.info("⏭️ No knowledge base configured, skipping pre-check")
            return {
                "question": question,
                "references": references,
                "kb_context": "",
            }

        try:
            # 使用混合检索获取知识库内容
            results = await embedding_service.hybrid_search_knowledge_base(
                db=db_session,
                query=question,
                knowledge_base_ids=knowledge_base_ids,
                top_k=settings.rag_top_k,
                similarity_threshold=settings.rag_similarity_threshold,
                mode="union",
            )

            if not results:
                logger.info("📭 No relevant content found in knowledge base")
                return {
                    "question": question,
                    "references": references,
                    "kb_context": "",
                }

            # 将知识库内容注入到 references 中
            # 使用特殊的 key 标识这是内部知识库的内容
            kb_contents = []
            for chunk in results:
                source = chunk.get("file_name", "内部知识库")
                content = chunk["content"]
                similarity = chunk.get("similarity", 0)
                kb_contents.append(f"[{source}] (相关度: {similarity:.2f})\n{content}")

            # 添加到 references，key 为 "内部知识库"
            updated_references = dict(references)
            updated_references["内部知识库"] = kb_contents

            # 同时生成 kb_context 供其他节点使用
            kb_context = "【内部知识库参考资料】\n" + "\n\n".join(kb_contents)

            logger.info(f"✅ KB Pre-Check: injected {len(kb_contents)} chunks from knowledge base")

            return {
                "question": question,
                "references": updated_references,
                "kb_context": kb_context,
            }

        except Exception as e:
            logger.error(f"KB Pre-Check failed: {e}")
            return {
                "question": question,
                "references": references,
                "kb_context": "",
            }

    return kb_precheck_node
