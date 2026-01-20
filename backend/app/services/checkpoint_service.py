"""
Checkpoint 查询服务

提供 LangGraph checkpoint 历史查询功能，用于实现消息分支导航。
所有方法直接使用 checkpointer 读取数据，无需实例化 Agent。
"""

from typing import Any

from loguru import logger

from app.core.checkpointer import create_checkpointer
from app.core.settings import Settings


class CheckpointService:
    """
    LangGraph Checkpoint 查询服务

    直接使用 checkpointer 读取数据，无需实例化 Agent，性能更高。
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_state_history(
        self,
        conversation_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        获取会话的 checkpoint 历史列表（直接读取 checkpointer）

        Args:
            conversation_id: 会话 ID
            limit: 返回数量限制

        Returns:
            checkpoint 列表
        """
        config = {"configurable": {"thread_id": str(conversation_id)}}

        async with create_checkpointer(self.settings) as checkpointer:
            return await self._collect_history(checkpointer, config, limit)

    async def get_sibling_checkpoints(
        self,
        conversation_id: int,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        """
        获取兄弟分支（深度锚点搜索版：解决中间节点导致的隔离问题）

        算法：
        1. 深度回溯找到真正的锚点（messageCount 变小的边界）
        2. 找到所有从锚点派生的后代
        3. 筛选出末端叶子节点
        """
        # 1. 获取足够的历史数据
        history = await self.get_state_history(conversation_id, limit=200)
        logger.info(
            f"[get_sibling_checkpoints] history count={len(history)}, checkpoint_id={checkpoint_id}"
        )

        if not history:
            return {"current": 0, "total": 1, "siblings": [checkpoint_id]}

        # 建立快速查找表
        cp_map = {h["checkpointId"]: h for h in history}

        # 2. 找到当前 Checkpoint
        current = cp_map.get(checkpoint_id)
        if not current:
            return {"current": 0, "total": 1, "siblings": [checkpoint_id]}

        current_count = current["messageCount"]

        # 3. 【核心修复】深度回溯寻找真正的分叉点 (True Fork Point)
        # 一直往上找，直到 messageCount 变小（代表回到了 AI 生成前的状态）
        anchor_id = None
        cursor_id = checkpoint_id

        # 防止死循环
        safety_break = 0
        while cursor_id and safety_break < 100:
            node = cp_map.get(cursor_id)
            if not node:
                break

            # 如果发现消息数量变少了，说明我们跨过了"生成阶段"
            if node["messageCount"] < current_count:
                anchor_id = cursor_id
                break

            # 如果已经是根节点了
            if not node["parentId"]:
                break

            # 继续向上回溯
            cursor_id = node["parentId"]
            safety_break += 1

        logger.info(
            f"[get_sibling_checkpoints] checkpoint={checkpoint_id} (cnt={current_count}) -> anchor={anchor_id}"
        )

        if not anchor_id:
            # 第一条消息或数据不完整
            return {"current": 0, "total": 1, "siblings": [checkpoint_id]}

        anchor_count = cp_map.get(anchor_id, {}).get("messageCount", 0)

        # 4. 辅助函数：检查 target 是否是 ancestor 的后代
        def is_descendant(target_id: str, ancestor_id: str) -> bool:
            curr = target_id
            sanity = 0
            while curr and sanity < 100:
                if curr == ancestor_id:
                    return True
                parent = cp_map.get(curr, {}).get("parentId")
                if not parent:
                    return False
                curr = parent
                sanity += 1
            return False

        # 5. 找到所有分支的候选节点
        # 条件：是 anchor 的后代，且 messageCount >= current_count
        candidates = []

        for h in history:
            h_id = h["checkpointId"]

            # 只检查消息数大于锚点的节点
            if h["messageCount"] <= anchor_count:
                continue

            # 检查是否是 Anchor 的后代
            if is_descendant(h_id, anchor_id):
                candidates.append(h_id)

        # 6. 筛选出"叶子节点" (不是其他候选节点的父节点)
        real_siblings = []

        for cand in candidates:
            # 检查 cand 是否是 candidates 中其他节点的 parent
            is_intermediate = False
            for potential_child in candidates:
                if potential_child == cand:
                    continue
                child_node = cp_map.get(potential_child)
                if child_node and child_node["parentId"] == cand:
                    is_intermediate = True
                    break

            if not is_intermediate:
                real_siblings.append(cand)

        # 确保当前节点在列表里
        if checkpoint_id not in real_siblings:
            real_siblings.append(checkpoint_id)

        # 去重并排序
        real_siblings = sorted(list(set(real_siblings)))

        # 计算索引
        try:
            current_index = real_siblings.index(checkpoint_id)
        except ValueError:
            current_index = len(real_siblings) - 1

        logger.info(f"[get_sibling_checkpoints] final siblings: {real_siblings}")

        return {
            "current": current_index,
            "total": len(real_siblings),
            "siblings": real_siblings,
        }

    async def get_checkpoint_messages(
        self,
        conversation_id: int,
        checkpoint_id: str,
    ) -> list[dict[str, Any]]:
        """
        获取指定 checkpoint 的消息列表（直接读取 checkpointer）

        Args:
            conversation_id: 会话 ID
            checkpoint_id: checkpoint ID

        Returns:
            消息列表
        """
        config = {
            "configurable": {
                "thread_id": str(conversation_id),
                "checkpoint_id": checkpoint_id,
            }
        }

        async with create_checkpointer(self.settings) as checkpointer:
            # 1. 查询目标 checkpoint 数据
            checkpoint_tuple = await checkpointer.aget(config)
            if not checkpoint_tuple:
                return []

            # 2. 提取 checkpoint 元信息
            messages, resolved_checkpoint_id, parent_id = self._extract_checkpoint_payload(
                checkpoint_tuple
            )

            # 3. 构建历史映射，便于为每条消息绑定所属 checkpoint
            history_map, _ = await self._load_history_map(
                checkpointer,
                {"configurable": {"thread_id": str(conversation_id)}},
            )
            checkpoint_parent_map = {
                key: value.get("parentId") for key, value in history_map.items()
            }
            message_checkpoint_map = self._calculate_message_checkpoint_map(
                history_map=history_map,
                target_checkpoint_id=resolved_checkpoint_id or checkpoint_id,
                message_count=len(messages),
            )

            # 4. 复用转换逻辑
            return self._transform_messages(
                messages=messages,
                conversation_id=str(conversation_id),
                message_checkpoint_map=message_checkpoint_map,
                checkpoint_parent_map=checkpoint_parent_map,
                fallback_checkpoint_id=resolved_checkpoint_id or checkpoint_id,
                fallback_parent_id=parent_id,
            )

    async def get_latest_messages(
        self,
        conversation_id: int,
    ) -> list[dict[str, Any]]:
        """
        直接从 Checkpointer 读取状态，无需构建 Graph 实例，性能更高。

        Args:
            conversation_id: 会话 ID

        Returns:
            消息列表，格式与前端 Message 类型兼容
        """
        config = {"configurable": {"thread_id": str(conversation_id)}}

        async with create_checkpointer(self.settings) as checkpointer:
            # 1. 读取最新 checkpoint
            checkpoint_tuple = await checkpointer.aget(config)
            logger.info(
                f"[get_latest_messages] checkpoint_tuple type={type(checkpoint_tuple)}, value={checkpoint_tuple}"
            )

            if not checkpoint_tuple:
                logger.info("[get_latest_messages] checkpoint_tuple is None/empty")
                return []

            # 调试：输出 checkpoint 属性
            logger.info(
                f"[get_latest_messages] hasattr checkpoint: {hasattr(checkpoint_tuple, 'checkpoint')}"
            )
            if hasattr(checkpoint_tuple, "checkpoint"):
                logger.info(
                    f"[get_latest_messages] checkpoint_tuple.checkpoint={checkpoint_tuple.checkpoint}"
                )

            messages, checkpoint_id, parent_id = self._extract_checkpoint_payload(checkpoint_tuple)
            logger.info(
                f"[get_latest_messages] extracted messages count={len(messages)}, checkpoint_id={checkpoint_id}"
            )

            # 2. 读取历史，用于推导每条消息的所属 checkpoint
            history_map, latest_id = await self._load_history_map(checkpointer, config)
            target_checkpoint_id = checkpoint_id or latest_id
            checkpoint_parent_map = {
                key: value.get("parentId") for key, value in history_map.items()
            }
            message_checkpoint_map = self._calculate_message_checkpoint_map(
                history_map=history_map,
                target_checkpoint_id=target_checkpoint_id,
                message_count=len(messages),
            )

            # 3. 转换消息并附带 checkpoint 元数据
            return self._transform_messages(
                messages=messages,
                conversation_id=str(conversation_id),
                message_checkpoint_map=message_checkpoint_map,
                checkpoint_parent_map=checkpoint_parent_map,
                fallback_checkpoint_id=target_checkpoint_id,
                fallback_parent_id=parent_id,
            )

    def _transform_messages(
        self,
        messages: list[Any],
        conversation_id: str,
        message_checkpoint_map: list[str | None] | None = None,
        checkpoint_parent_map: dict[str, str | None] | None = None,
        fallback_checkpoint_id: str | None = None,
        fallback_parent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        独立的消息转换逻辑，遵循单一职责原则
        """
        result = []

        for idx, msg in enumerate(messages):
            # 1. 基础属性提取（兼容 dict 或 Object）
            msg_type = getattr(msg, "type", None) or (
                msg.get("type") if isinstance(msg, dict) else None
            )
            content = getattr(msg, "content", "") or (
                msg.get("content", "") if isinstance(msg, dict) else ""
            )

            # 2. 角色映射
            if msg_type == "human":
                role = "user"
                sender_id = "0"
            elif msg_type == "ai":
                role = "assistant"
                sender_id = "-1"
            elif msg_type == "system":
                # 不显示系统提示词
                continue
            elif msg_type == "tool":
                # 不显示工具调用结果
                continue
            else:
                role = "unknown"
                sender_id = "unknown"

            # 3. 处理工具调用请求（AI 消息可能只有 tool_calls 没有 content）
            if role == "assistant" and not content:
                tool_calls = getattr(msg, "tool_calls", [])
                if tool_calls:
                    # 有工具调用但无内容的中间消息，跳过
                    continue
                else:
                    # 既没内容也没工具调用的空消息，跳过
                    continue

            # 4. 构造 DTO，使用稳定的消息 ID
            msg_id = getattr(msg, "id", None) or f"{conversation_id}_{idx}"

            # 5. 计算 checkpoint 元信息
            checkpoint_id = None
            if message_checkpoint_map and idx < len(message_checkpoint_map):
                checkpoint_id = message_checkpoint_map[idx]
            if not checkpoint_id:
                checkpoint_id = fallback_checkpoint_id

            parent_id = None
            if checkpoint_parent_map and checkpoint_id:
                parent_id = checkpoint_parent_map.get(checkpoint_id) or fallback_parent_id
            else:
                parent_id = fallback_parent_id

            # 6. 尝试获取时间戳
            additional_kwargs = getattr(msg, "additional_kwargs", {}) or {}
            create_time = additional_kwargs.get("created_at")

            result.append(
                {
                    "id": str(msg_id),
                    "conversationId": conversation_id,
                    "senderId": sender_id,
                    "role": role,
                    "content": content,
                    "contentType": "TEXT",
                    "createTime": create_time,
                    "checkpointId": checkpoint_id,
                    "parentCheckpointId": parent_id,
                }
            )

        return result

    async def _collect_history(
        self,
        checkpointer: Any,
        config: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        1. 收集 checkpoint 历史，避免多处重复代码。
        """
        history = []
        async for checkpoint_tuple in checkpointer.alist(config, limit=limit):
            # CheckpointTuple 是对象，使用属性访问
            checkpoint = checkpoint_tuple.checkpoint or {}
            parent_config = checkpoint_tuple.parent_config or {}
            channel_values = checkpoint.get("channel_values", {}) or {}
            messages = channel_values.get("messages", []) or []

            # parent_id 从 parent_config 的 checkpoint_id 获取
            parent_id = None
            if parent_config:
                configurable = parent_config.get("configurable", {}) or {}
                parent_id = configurable.get("checkpoint_id")

            history.append(
                {
                    "checkpointId": checkpoint.get("id"),
                    "parentId": parent_id,
                    "messageCount": len(messages),
                }
            )
        return history

    async def _load_history_map(
        self,
        checkpointer: Any,
        config: dict[str, Any],
        limit: int = 200,
    ) -> tuple[dict[str, dict[str, Any]], str | None]:
        """
        1. 将 checkpoint 历史转换为便于查询的 Map，并返回最新 checkpointId。
        """
        history_map: dict[str, dict[str, Any]] = {}
        latest_checkpoint_id: str | None = None

        async for checkpoint_tuple in checkpointer.alist(config, limit=limit):
            # CheckpointTuple 是对象，使用属性访问
            checkpoint = checkpoint_tuple.checkpoint or {}
            parent_config = checkpoint_tuple.parent_config or {}
            channel_values = checkpoint.get("channel_values", {}) or {}
            messages = channel_values.get("messages", []) or []

            checkpoint_id = checkpoint.get("id")
            # parent_id 从 parent_config 的 checkpoint_id 获取
            parent_id = None
            if parent_config:
                configurable = parent_config.get("configurable", {}) or {}
                parent_id = configurable.get("checkpoint_id")

            if checkpoint_id and latest_checkpoint_id is None:
                latest_checkpoint_id = checkpoint_id
            if checkpoint_id:
                history_map[checkpoint_id] = {
                    "parentId": parent_id,
                    "messageCount": len(messages),
                }

        return history_map, latest_checkpoint_id

    def _calculate_message_checkpoint_map(
        self,
        history_map: dict[str, dict[str, Any]],
        target_checkpoint_id: str | None,
        message_count: int,
    ) -> list[str | None]:
        """
        1. 根据 checkpoint 链路推导每条消息所属的 checkpoint，用于在 UI 展示 1/2 导航。
        """
        if not target_checkpoint_id or target_checkpoint_id not in history_map:
            return [target_checkpoint_id] * message_count

        # 1. 构建从根到目标的链路，保证 messageCount 单调递增
        chain: list[str] = []
        cursor = target_checkpoint_id
        while cursor:
            chain.append(cursor)
            parent_id = history_map.get(cursor, {}).get("parentId")
            if not parent_id or parent_id in chain:
                break
            cursor = parent_id
        chain.reverse()

        # 2. 根据 messageCount 差值映射每个索引
        mapping: list[str | None] = [None] * message_count
        prev_count = 0
        for checkpoint_id in chain:
            item = history_map.get(checkpoint_id, {})
            current_count = item.get("messageCount", prev_count)
            if current_count <= prev_count:
                continue
            for idx in range(prev_count, min(current_count, message_count)):
                mapping[idx] = checkpoint_id
            prev_count = current_count

        # 3. 填充仍为空的索引，保持兜底可用
        for idx in range(message_count):
            if mapping[idx] is None:
                mapping[idx] = target_checkpoint_id

        return mapping

    def _extract_checkpoint_payload(
        self,
        checkpoint_tuple: Any,
    ) -> tuple[list[Any], str | None, str | None]:
        """
        兼容 aget 返回的格式，提取消息、checkpointId 与父 checkpointId。

        注意：AsyncPostgresSaver.aget() 直接返回 checkpoint dict（不是 CheckpointTuple）
        格式：{'id': '...', 'channel_values': {'messages': [...]}, ...}
        """
        # 判断是 dict 还是 CheckpointTuple
        if isinstance(checkpoint_tuple, dict):
            # aget 返回的直接是 checkpoint dict
            channel_values = checkpoint_tuple.get("channel_values", {}) or {}
            messages = channel_values.get("messages", []) or []
            checkpoint_id = checkpoint_tuple.get("id")
            # dict 格式没有 parent_config，无法获取 parent_id
            parent_id = None
        else:
            # alist 返回的是 CheckpointTuple 对象
            checkpoint = getattr(checkpoint_tuple, "checkpoint", None) or {}
            parent_config = getattr(checkpoint_tuple, "parent_config", None) or {}
            channel_values = checkpoint.get("channel_values", {}) or {}
            messages = channel_values.get("messages", []) or []
            checkpoint_id = checkpoint.get("id")

            # parent_id 从 parent_config 的 checkpoint_id 获取
            parent_id = None
            if parent_config:
                configurable = parent_config.get("configurable", {}) or {}
                parent_id = configurable.get("checkpoint_id")

        return messages, checkpoint_id, parent_id
