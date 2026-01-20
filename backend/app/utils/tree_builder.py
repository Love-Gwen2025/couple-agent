"""
通用树形结构构建工具

支持将扁平列表构建为树形结构：
1. 支持无限层级递归
2. 支持关键词过滤（可选）
3. 自动校验循环引用和ID冲突
4. 支持自定义字段名（通过回调函数）

使用示例:
    from app.utils.tree_builder import TreeBuilder

    # 方式1: 使用字典
    messages = [
        {"id": 1, "parent_id": None, "content": "你好"},
        {"id": 2, "parent_id": 1, "content": "你好！"},
        {"id": 3, "parent_id": 2, "content": "天气如何"},
    ]
    tree = TreeBuilder.build(messages)

    # 方式2: 使用 dataclass 或 Pydantic model
    tree = TreeBuilder.build(
        items=messages,
        get_id=lambda x: x.id,
        get_parent_id=lambda x: x.parent_id,
    )

    # 方式3: 带关键词过滤
    tree = TreeBuilder.build(
        items=messages,
        keyword="天气",
        matchers=[lambda x: x.get("content", "")],
    )
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class TreeBuildError(Exception):
    """树构建异常"""

    pass


class TreeBuilder:
    """
    通用树形结构构建器

    设计原则：
    1. 默认约定优于配置（默认使用 id/parent_id/children 字段名）
    2. 支持自定义字段访问器
    3. 类型安全（使用 TypeVar 支持泛型）
    """

    @staticmethod
    def build(
        items: list[T],
        get_id: Callable[[T], int | str | None] | None = None,
        get_parent_id: Callable[[T], int | str | None] | None = None,
        set_children: Callable[[T, list[T]], None] | None = None,
        keyword: str | None = None,
        matchers: list[Callable[[T], str]] | None = None,
        validate: bool = True,
    ) -> list[T]:
        """
        构建树形结构（支持无限层级递归）

        Args:
            items: 原始数据列表（可以是 dict、dataclass、Pydantic model 等）
            get_id: 获取节点ID的函数，默认为 lambda x: x["id"] 或 x.id
            get_parent_id: 获取父节点ID的函数，默认为 lambda x: x["parent_id"] 或 x.parent_id
            set_children: 设置子节点的函数，默认为 lambda x, c: x["children"] = c 或 x.children = c
            keyword: 关键词过滤（可选）
            matchers: 关键词匹配器列表（可选），每个匹配器返回待匹配的字符串
            validate: 是否校验树结构（循环引用、ID冲突），默认 True

        Returns:
            树形结构的根节点列表

        Raises:
            TreeBuildError: 当检测到循环引用或重复ID时抛出
        """
        if not items:
            return []

        # 自动推断访问器
        get_id = get_id or TreeBuilder._default_get_id
        get_parent_id = get_parent_id or TreeBuilder._default_get_parent_id
        set_children = set_children or TreeBuilder._default_set_children

        # 1. 校验树结构
        if validate:
            TreeBuilder.validate_structure(items, get_id, get_parent_id)

        # 2. 构建 ID -> 节点 映射
        node_map: dict[Any, T] = {}
        for item in items:
            node_id = get_id(item)
            if node_id is not None:
                node_map[node_id] = item

        # 3. 关键词过滤：找到所有匹配的节点
        if keyword and matchers:
            matched_nodes = TreeBuilder._filter_by_keyword(items, keyword, matchers)
        else:
            matched_nodes = items.copy()

        # 4. 找到所有需要保留的节点（匹配节点 + 祖先节点）
        required_ids = TreeBuilder._find_required_nodes(
            matched_nodes, node_map, get_id, get_parent_id
        )

        # 5. 过滤出需要的节点
        filtered_items = [item for item in items if get_id(item) in required_ids]

        # 6. 找出根节点
        roots = [
            item
            for item in filtered_items
            if get_parent_id(item) is None or get_parent_id(item) == 0
        ]

        # 7. 按父节点分组子节点
        children_map: dict[Any, list[T]] = {}
        for item in filtered_items:
            parent_id = get_parent_id(item)
            if parent_id is not None and parent_id != 0:
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(item)

        # 8. 递归构建树
        for root in roots:
            TreeBuilder._build_recursively(root, children_map, get_id, set_children)

        return roots

    @staticmethod
    def validate_structure(
        items: list[T],
        get_id: Callable[[T], int | str | None],
        get_parent_id: Callable[[T], int | str | None],
    ) -> None:
        """
        校验树结构是否合法

        检查：
        1. ID 是否重复
        2. 是否存在循环引用

        Raises:
            TreeBuildError: 当检测到问题时抛出
        """
        id_to_parent: dict[Any, Any] = {}

        # 检测重复 ID
        for item in items:
            node_id = get_id(item)
            parent_id = get_parent_id(item)

            if node_id is None:
                continue

            if node_id in id_to_parent:
                raise TreeBuildError(f"重复的节点ID: {node_id}")

            id_to_parent[node_id] = parent_id

        # 检测循环引用
        for node_id in id_to_parent:
            visited: set[Any] = set()
            current_id = node_id

            while current_id is not None and current_id != 0:
                if current_id in visited:
                    raise TreeBuildError(f"检测到循环引用，涉及节点: {visited}")
                visited.add(current_id)
                current_id = id_to_parent.get(current_id)

    @staticmethod
    def find_path_to_root(
        node_id: int | str,
        node_map: dict[Any, T],
        get_id: Callable[[T], int | str | None],
        get_parent_id: Callable[[T], int | str | None],
    ) -> list[T]:
        """
        从指定节点向上遍历到根节点，返回路径

        用于：根据 current_message_id 找到当前分支的完整消息列表

        Args:
            node_id: 起始节点ID
            node_map: ID -> 节点 映射
            get_id: 获取节点ID的函数
            get_parent_id: 获取父节点ID的函数

        Returns:
            从根节点到指定节点的路径列表（按时间顺序）
        """
        path: list[T] = []
        current_id = node_id

        while current_id is not None and current_id in node_map:
            node = node_map[current_id]
            path.append(node)
            current_id = get_parent_id(node)

        # 反转，使路径从根到叶
        path.reverse()
        return path

    @staticmethod
    def find_siblings(
        node: T,
        node_map: dict[Any, T],
        get_id: Callable[[T], int | str | None],
        get_parent_id: Callable[[T], int | str | None],
        all_items: list[T],
    ) -> list[T]:
        """
        找到节点的所有兄弟节点（相同 parent_id）

        用于：实现版本切换 <1/2>

        Returns:
            兄弟节点列表（包含自身）
        """
        parent_id = get_parent_id(node)
        return [item for item in all_items if get_parent_id(item) == parent_id]

    # ==================== 私有方法 ====================

    @staticmethod
    def _default_get_id(item: Any) -> int | str | None:
        """默认的 ID 获取器"""
        if isinstance(item, dict):
            return item.get("id")
        return getattr(item, "id", None)

    @staticmethod
    def _default_get_parent_id(item: Any) -> int | str | None:
        """默认的 parent_id 获取器"""
        if isinstance(item, dict):
            return item.get("parent_id") or item.get("parentId") or item.get("parent_message_id")
        return getattr(item, "parent_id", None) or getattr(item, "parent_message_id", None)

    @staticmethod
    def _default_set_children(item: Any, children: list[Any]) -> None:
        """默认的 children 设置器"""
        if isinstance(item, dict):
            item["children"] = children
        else:
            item.children = children

    @staticmethod
    def _filter_by_keyword(
        items: list[T],
        keyword: str,
        matchers: list[Callable[[T], str]],
    ) -> list[T]:
        """根据关键词过滤节点"""
        keyword_lower = keyword.lower()
        matched: list[T] = []

        for item in items:
            for matcher in matchers:
                try:
                    value = matcher(item)
                    if value and keyword_lower in value.lower():
                        matched.append(item)
                        break
                except Exception:
                    continue

        return matched

    @staticmethod
    def _find_required_nodes(
        matched_nodes: list[T],
        node_map: dict[Any, T],
        get_id: Callable[[T], int | str | None],
        get_parent_id: Callable[[T], int | str | None],
    ) -> set[Any]:
        """找到所有需要保留的节点ID（匹配节点 + 祖先）"""
        required_ids: set[Any] = set()

        for node in matched_nodes:
            node_id = get_id(node)
            if node_id is not None:
                required_ids.add(node_id)

            # 向上追溯祖先
            current_parent_id = get_parent_id(node)
            while current_parent_id is not None and current_parent_id != 0:
                if current_parent_id in required_ids:
                    break  # 祖先已记录
                required_ids.add(current_parent_id)

                parent_node = node_map.get(current_parent_id)
                if parent_node is None:
                    break
                current_parent_id = get_parent_id(parent_node)

        return required_ids

    @staticmethod
    def _build_recursively(
        current_node: T,
        children_map: dict[Any, list[T]],
        get_id: Callable[[T], int | str | None],
        set_children: Callable[[T, list[T]], None],
    ) -> None:
        """递归构建子树"""
        node_id = get_id(current_node)
        children = children_map.get(node_id, [])

        # 递归处理每个子节点
        for child in children:
            TreeBuilder._build_recursively(child, children_map, get_id, set_children)

        set_children(current_node, children)
