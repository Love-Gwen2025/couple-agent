"""
DeepSearch 规划节点 (Planning Node)

负责分析用户问题，判断是否需要联网搜索，生成搜索关键词。
使用推理模型的"思考能力"进行多轮规划。
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.utils.content import extract_text_content

PLANNING_PROMPT = """你是一个联网信息搜索专家，你需要根据用户的问题，通过联网搜索来搜集相关信息，然后根据这些信息来回答用户的问题。

# 用户问题：
{question}    
    
# 当前已知资料

{reference}

# 当前环境信息

{meta_info}

# 任务
- 判断「当前已知资料」是否已经足够回答用户的问题
- 如果「当前已知资料」已经足够回答用户的问题，返回"无需检索"，不要输出任何其他多余的内容
- 如果判断「当前已知资料」还不足以回答用户的问题，思考还需要搜索什么信息，输出对应的关键词，请保证每个关键词的精简和独立性
- 输出的每个关键词都应该要具体到可以用于独立检索，要包括完整的主语和宾语，避免歧义和使用代词，关键词之间不能有指代关系
- 可以输出1 ～ {max_search_words}个关键词，当暂时无法提出足够准确的关键词时，请适当地减少关键词的数量
- 输出多个关键词时，关键词之间用 ; 分割，不要输出其他任何多余的内容

# 你的回答：
"""  # noqa: W291


def parse_search_queries(output: str) -> list[str] | None:
    """
    解析模型输出，提取搜索关键词。

    Returns:
        关键词列表，如果无需搜索则返回 None
    """
    if "无需" in output:
        return None
    # 按分号分割，过滤空白
    queries = [q.strip() for q in output.split(";") if q.strip()]
    return queries if queries else None


def format_references(references: dict[str, list[str]]) -> str:
    """将参考资料格式化为文本"""
    if not references:
        return "暂无已知资料"

    output = ""
    for query, results in references.items():
        output += f"【查询 {query} 得到的相关资料】"
        for i, result in enumerate(results, 1):
            output += f"参考{i}: {result}\n"
    return output


def create_planning_node(model, settings):
    """
    创建规划节点

    Args:
        model: LangChain 模型实例
        settings: 应用配置

    Returns:
        节点函数
    """
    from datetime import datetime

    async def planning_node(state: dict[str, Any]) -> dict[str, Any]:
        """
        规划节点：分析问题，生成搜索关键词或判断无需搜索。
        """
        messages = state.get("messages", [])
        references = state.get("references", {})
        planning_rounds = state.get("planning_rounds", 0)
        question = state.get("question", "")

        # 如果没有明确的 question，从最后一条用户消息提取
        if not question:
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    question = msg.content
                    break

        logger.info(f"🧠 Planning round {planning_rounds + 1}, question: {question[:50]}...")

        # 构建 prompt
        prompt = PLANNING_PROMPT.format(
            question=question,
            reference=format_references(references),
            meta_info=f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            max_search_words=5,
        )

        try:
            response = await model.ainvoke(
                [
                    SystemMessage(content="你是一个深度研究助手，擅长分析问题并规划搜索策略。"),
                    HumanMessage(content=prompt),
                ]
            )

            output = extract_text_content(response.content).strip()
            logger.info(f"🧠 Planning output: {output[:100]}...")

            # 解析搜索关键词
            queries = parse_search_queries(output)

            if queries:
                logger.info(f"🔍 Generated search queries: {queries}")
                return {
                    "search_queries": queries,
                    "planning_rounds": planning_rounds + 1,
                    "question": question,
                }
            else:
                logger.info("✅ No more search needed, proceeding to summary")
                return {
                    "search_queries": [],
                    "planning_rounds": planning_rounds + 1,
                    "question": question,
                }

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            # 出错时直接进入总结阶段
            return {
                "search_queries": [],
                "planning_rounds": planning_rounds + 1,
                "question": question,
            }

    return planning_node
