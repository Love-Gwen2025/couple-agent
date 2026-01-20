"""
Chatbot 节点 (Chatbot Node)

普通对话模式的核心节点，负责调用 LLM 获取回复或决定工具调用。
"""

from typing import Any

from langchain_core.messages import BaseMessage
from loguru import logger


def create_chatbot_node(model):
    """
    创建 Chatbot 节点

    Args:
        model: 绑定了工具的 LangChain 模型实例 (model.bind_tools())

    Returns:
        节点函数
    """

    async def chatbot_node(state: dict[str, Any]) -> dict[str, list[BaseMessage]]:
        """
        Chatbot 节点：调用 LLM 获取回复或工具调用决策。

        输入 state:
          - messages: 消息列表

        输出 state:
          - messages: 追加 AI 响应
        """
        messages = state.get("messages", [])
        logger.info(f"🤖 Chatbot receiving {len(messages)} messages")

        response = await model.ainvoke(messages)

        # 记录响应信息
        has_tool_calls = bool(response.tool_calls) if hasattr(response, "tool_calls") else False
        content_len = len(response.content) if response.content else 0
        logger.info(
            f"🤖 Chatbot response: has_tool_calls={has_tool_calls}, content_len={content_len}"
        )

        if has_tool_calls:
            logger.info(f"🔧 Tool calls: {[tc['name'] for tc in response.tool_calls]}")

        return {"messages": [response]}

    return chatbot_node
