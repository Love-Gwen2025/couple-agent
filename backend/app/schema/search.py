"""
搜索相关的枚举和类型定义
"""

from enum import Enum


class SearchStrategy(Enum):
    """知识库搜索策略"""

    BASIC = "basic"  # 纯向量检索
    HYBRID = "hybrid"  # 向量 + BM25 混合检索
    ADVANCED = "advanced"  # Query Rewrite + Hybrid + Rerank
