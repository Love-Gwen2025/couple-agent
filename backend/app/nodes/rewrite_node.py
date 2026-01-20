"""
代词消解节点 (Rewrite Node)

用于在调用工具之前，将用户消息中的代词（如"它"、"那个"）
替换为具体的实体名称，提高工具调用的准确性。

例如：
- 用户: "它的价格是多少？"
- 上下文: 之前讨论的是 iPhone 15
- 重写后: "iPhone 15 的价格是多少？"
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

REWRITE_PROMPT = """你是一个查询重写专家。你的任务是将用户的查询进行代词消解，使其更加明确。

规则：
1. 如果用户消息中包含代词（如"它"、"这个"、"那个"、"他"、"她"等），根据对话历史将其替换为具体的实体名称
2. 如果用户消息已经足够清晰，直接返回原始消息
3. 只返回重写后的查询，不要添加任何解释
4. 保持用户的原始意图不变

示例：
对话历史: "用户: iPhone 15 怎么样？助手: iPhone 15 是一款很棒的手机..."
用户消息: "它多少钱？"
重写结果: "iPhone 15 多少钱？"
"""


async def rewrite_query(
    state: dict[str, Any],
    model,
) -> dict[str, Any]:
    """
    代词消解节点

    输入 state:
      - messages: 消息列表

    输出 state:
      - messages: 可能被重写后的消息列表
    """
    messages = state.get("messages", [])

    if not messages:
        return state

    # 获取最后一条用户消息
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        return state

    original_query = last_message.content

    # 如果消息很短或没有明显的代词，跳过重写
    pronouns = ["它", "这个", "那个", "他", "她", "他们", "她们", "这", "那"]
    has_pronoun = any(p in original_query for p in pronouns)

    if not has_pronoun or len(messages) <= 1:
        logger.debug(f"Skipping rewrite for: {original_query}")
        return state

    try:
        # 构建历史上下文（最近几条消息）
        history_context = []
        for msg in messages[-6:-1]:  # 最近5条历史
            if isinstance(msg, HumanMessage):
                history_context.append(f"用户: {msg.content}")
            else:
                content = msg.content if hasattr(msg, "content") else str(msg)
                history_context.append(f"助手: {content[:200]}")  # 限制长度

        history_str = "\n".join(history_context) if history_context else "无历史"

        # 调用 LLM 进行重写
        rewrite_messages = [
            SystemMessage(content=REWRITE_PROMPT),
            HumanMessage(
                content=f"对话历史:\n{history_str}\n\n用户消息: {original_query}\n\n重写结果:"
            ),
        ]

        response = await model.ainvoke(rewrite_messages)
        rewritten_query = response.content.strip()

        # 如果重写结果与原始查询不同，更新消息
        if rewritten_query and rewritten_query != original_query:
            logger.info(f"Query rewritten: '{original_query}' -> '{rewritten_query}'")
            # 创建新的消息列表，替换最后一条
            new_messages = messages[:-1] + [HumanMessage(content=rewritten_query)]
            return {"messages": new_messages}

    except Exception as e:
        logger.warning(f"Query rewrite failed: {e}, using original query")

    return state


def create_rewrite_node(model):
    """
    创建代词消解节点

    Args:
        model: LangChain 模型实例

    Returns:
        节点函数
    """

    async def node(state: dict[str, Any]) -> dict[str, Any]:
        return await rewrite_query(state, model)

    return node
