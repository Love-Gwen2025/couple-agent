"""
DeepSearch 搜索节点 (Search Node)

负责执行联网搜索，获取参考资料。
使用 Tavily API 进行搜索。
"""

from typing import Any

from loguru import logger


def create_search_node(settings):
    """
    创建搜索节点

    Args:
        settings: 应用配置

    Returns:
        节点函数
    """
    # 延迟导入，避免未安装 tavily 时报错
    from tavily import TavilyClient

    async def search_node(state: dict[str, Any]) -> dict[str, Any]:
        """
        搜索节点：执行联网搜索，将结果累积到参考资料中。
        """
        import asyncio

        search_queries = state.get("search_queries", [])
        references = state.get("references", {}).copy()

        if not search_queries:
            logger.warning("⚠️ No search queries provided")
            return {"references": references}

        if not settings.tavily_api_key:
            logger.error("❌ Tavily API key not configured")
            return {"references": references}

        logger.info(f"🔍 Searching for: {search_queries}")

        try:
            client = TavilyClient(api_key=settings.tavily_api_key)

            async def search_single(query: str) -> tuple[str, list[str]]:
                """搜索单个关键词"""
                try:
                    # Tavily 是同步 API，使用 to_thread 包装
                    result = await asyncio.to_thread(
                        client.search,
                        query=query,
                        search_depth="basic",
                        max_results=5,
                    )
                    # 提取搜索结果
                    contents = []
                    for item in result.get("results", []):
                        title = item.get("title", "")
                        content = item.get("content", "")
                        url = item.get("url", "")
                        formatted = f"标题: {title}\n内容: {content}\n来源: {url}"
                        contents.append(formatted)
                    return query, contents
                except Exception as e:
                    logger.error(f"Search failed for '{query}': {e}")
                    return query, []

            # 并发执行所有搜索
            tasks = [search_single(q) for q in search_queries]
            results = await asyncio.gather(*tasks)

            # 合并结果到 references
            for query, contents in results:
                if contents:
                    if query in references:
                        references[query].extend(contents)
                    else:
                        references[query] = contents
                    logger.info(f"✅ Got {len(contents)} results for '{query}'")

        except Exception as e:
            logger.error(f"Search node failed: {e}")

        return {"references": references, "search_queries": []}

    return search_node
