"""
DeepSearch 总结节点 (Summary Node)

负责根据收集到的参考资料，生成最终的综合性回答。
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

from app.utils.content import extract_text_content

SUMMARY_PROMPT = """# 联网参考资料
{reference}

# 当前环境信息
{meta_info}

# 任务
- 直接回答用户问题，不要重复搜索关键词或查询语句。
- 优先参考「联网参考资料」中的信息进行回复。
- 回复请使用清晰、结构化（序号/分段等）的语言，确保用户轻松理解和使用。
- 如果回复内容中参考了资料，请务必在正文的段落中引用对应的参考编号，例如[1][2]
- 回答的最后需要列出已参考的所有资料信息。格式如下：[参考编号] 资料名称
示例：
[1] 火山引擎
[2] 火山方舟大模型服务平台

# 用户问题
{question}

# 重要提示
请直接开始回答问题，不要输出搜索词、查询关键词或"无需检索"等内容。

# 你的回答：(直接开始正文)
"""


def format_references_for_summary(references: dict[str, list[str]]) -> str:
    """将参考资料格式化为带编号的文本"""
    if not references:
        return "暂无参考资料"

    output = ""
    ref_idx = 1
    for query, results in references.items():
        output += f"\n【查询 '{query}' 得到的相关资料】\n"
        for result in results:
            output += f"[{ref_idx}] {result}\n"
            ref_idx += 1
    return output


def create_summary_node(model):
    """
    创建总结节点

    Args:
        model: LangChain 模型实例

    Returns:
        节点函数
    """
    from datetime import datetime

    async def summary_node(state: dict[str, Any]) -> dict[str, Any]:
        """
        总结节点：根据参考资料生成最终回答。
        """
        references = state.get("references", {})
        question = state.get("question", "")
        messages = state.get("messages", [])

        # 如果没有明确的 question，从最后一条用户消息提取
        if not question:
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    question = msg.content
                    break

        logger.info(f"📝 Generating summary for: {question[:50]}...")
        logger.info(f"📚 Using {len(references)} reference groups")

        # 构建 prompt
        prompt = SUMMARY_PROMPT.format(
            reference=format_references_for_summary(references),
            meta_info=f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            question=question,
        )

        try:
            response = await model.ainvoke(
                [
                    SystemMessage(
                        content="你是一个深度研究助手，擅长综合多方资料给出全面、准确的回答。"
                    ),
                    HumanMessage(content=prompt),
                ]
            )

            summary = extract_text_content(response.content).strip()
            logger.info(f"📝 Summary generated: {len(summary)} chars")

            # 返回 AI 消息
            return {
                "messages": [AIMessage(content=summary)],
                # 清理临时状态
                "search_queries": [],
            }

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "messages": [AIMessage(content=f"抱歉，生成回答时出错：{e}")],
                "search_queries": [],
            }

    return summary_node
