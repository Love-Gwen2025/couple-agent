"""
Tavily 网络搜索工具

用于搜索互联网上的实时信息。
当用户询问需要最新信息的问题时使用。
"""

from functools import lru_cache

from langchain_core.tools import tool
from loguru import logger

from app.core.settings import get_settings


@lru_cache
def _get_tavily_client():
    """
    获取 Tavily 客户端（懒加载）
    """
    settings = get_settings()

    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured")
        return None

    try:
        from tavily import TavilyClient

        return TavilyClient(api_key=settings.tavily_api_key)
    except ImportError:
        logger.error("tavily-python package not installed. Run: pip install tavily-python")
        return None


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    在互联网上搜索信息。

    当用户询问以下类型的问题时使用此工具：
    - 最新新闻或时事
    - 需要实时数据的问题（如天气、股价、赛事结果）
    - 你的知识库中没有的信息
    - 需要验证的事实

    Args:
        query: 搜索查询词
        max_results: 返回的最大结果数量，默认5条

    Returns:
        搜索结果摘要
    """
    client = _get_tavily_client()

    if not client:
        return "网络搜索服务未配置。请联系管理员配置 Tavily API Key。"

    try:
        response = client.search(
            query=query,
            max_results=max_results,
            include_answer=True,
            search_depth="basic",
        )

        # 如果有直接答案
        if response.get("answer"):
            result = f"答案: {response['answer']}\n\n"
        else:
            result = ""

        # 添加搜索结果
        if response.get("results"):
            result += "搜索结果:\n"
            for i, item in enumerate(response["results"], 1):
                title = item.get("title", "无标题")
                content = item.get("content", "")[:200]  # 限制长度
                url = item.get("url", "")
                result += f"{i}. {title}\n   {content}...\n   来源: {url}\n\n"

        return result if result else "未找到相关搜索结果。"

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return f"搜索时发生错误: {e}"
