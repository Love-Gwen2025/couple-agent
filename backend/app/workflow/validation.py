from __future__ import annotations

from dataclasses import dataclass
from typing import DefaultDict

from collections import defaultdict, deque

from app.workflow.definition import WorkflowDefinition, WorkflowNode

_RESERVED_NODE_IDS = {"__tools__"}


@dataclass(frozen=True)
class ValidatedWorkflow:
    definition: WorkflowDefinition
    start_node_id: str
    end_node_id: str
    llm_node_id: str
    nodes_by_id: dict[str, WorkflowNode]
    edges_by_source: dict[str, list]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_workflow_definition(definition: WorkflowDefinition) -> ValidatedWorkflow:
    """
    校验 workflow definition（DAG + MVP 语义约束）。

    约束（MVP）：
    - 恰好 1 个 start、1 个 end、且恰好 1 个 llm
    - 无环（DAG）
    - 所有节点从 start 可达、且能到达 end
    - 仅 router 允许多出边；router 的每条出边必须带唯一 case
    - 非 router（除 end）必须恰好 1 条出边；end 必须 0 出边
    """
    _require(definition.schemaVersion == 1, "不支持的 schemaVersion（当前仅支持 1）")
    _require(definition.nodes, "workflow.nodes 不能为空")

    nodes_by_id: dict[str, WorkflowNode] = {}
    for node in definition.nodes:
        _require(node.id not in _RESERVED_NODE_IDS, f"节点 id 不允许使用保留值: {node.id}")
        _require(node.id not in nodes_by_id, f"节点 id 重复: {node.id}")
        nodes_by_id[node.id] = node

    start_nodes = [n for n in definition.nodes if n.type == "start"]
    end_nodes = [n for n in definition.nodes if n.type == "end"]
    llm_nodes = [n for n in definition.nodes if n.type == "llm"]

    _require(len(start_nodes) == 1, "必须且只能包含 1 个 start 节点")
    _require(len(end_nodes) == 1, "必须且只能包含 1 个 end 节点")
    _require(len(llm_nodes) == 1, "必须且只能包含 1 个 llm 节点（MVP 限制）")

    start_node_id = start_nodes[0].id
    end_node_id = end_nodes[0].id
    llm_node_id = llm_nodes[0].id

    # 边基础校验
    edges_by_source: DefaultDict[str, list] = defaultdict(list)
    in_degree: DefaultDict[str, int] = defaultdict(int)
    for edge in definition.edges:
        _require(edge.source in nodes_by_id, f"edge.source 不存在: {edge.source}")
        _require(edge.target in nodes_by_id, f"edge.target 不存在: {edge.target}")
        _require(edge.source != edge.target, "不允许自环边（source == target）")
        edges_by_source[edge.source].append(edge)
        in_degree[edge.target] += 1

    _require(in_degree[start_node_id] == 0, "start 节点不允许有入边")
    _require(edges_by_source.get(end_node_id, []) == [], "end 节点不允许有出边")

    # 出边规则校验
    for node_id, node in nodes_by_id.items():
        outgoing = edges_by_source.get(node_id, [])

        if node.type == "end":
            _require(len(outgoing) == 0, "end 节点必须 0 出边")
            continue

        if node.type == "router":
            _require(len(outgoing) >= 1, "router 节点必须至少 1 条出边")
            cases = []
            for e in outgoing:
                _require(bool(e.case), "router 的每条出边必须设置 case")
                cases.append(e.case)
            _require(len(cases) == len(set(cases)), "router 出边 case 必须唯一")
            continue

        # 非 router 节点（包括 start / context / llm / verify）
        _require(len(outgoing) == 1, f"节点 {node_id}（type={node.type}）必须恰好 1 条出边")
        # 非 router 出边不应携带 case（避免歧义）
        only_edge = outgoing[0]
        _require(only_edge.case in (None, ""), "非 router 节点的出边不允许设置 case")

    # DAG 无环校验（Kahn）
    in_deg = dict(in_degree)
    for node_id in nodes_by_id:
        in_deg.setdefault(node_id, 0)

    queue = deque([nid for nid, deg in in_deg.items() if deg == 0])
    visited = 0
    while queue:
        nid = queue.popleft()
        visited += 1
        for e in edges_by_source.get(nid, []):
            in_deg[e.target] -= 1
            if in_deg[e.target] == 0:
                queue.append(e.target)

    _require(visited == len(nodes_by_id), "workflow 必须是 DAG（检测到环或不可达节点）")

    # 可达性：start -> all
    def reachable_from(start: str) -> set[str]:
        seen = set()
        dq = deque([start])
        while dq:
            cur = dq.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            for e in edges_by_source.get(cur, []):
                dq.append(e.target)
        return seen

    reach = reachable_from(start_node_id)
    _require(len(reach) == len(nodes_by_id), "存在从 start 不可达的节点")

    # 可达性：all -> end（反向图）
    reverse_edges: DefaultDict[str, list[str]] = defaultdict(list)
    for src, edges in edges_by_source.items():
        for e in edges:
            reverse_edges[e.target].append(src)

    can_reach_end = set()
    dq = deque([end_node_id])
    while dq:
        cur = dq.popleft()
        if cur in can_reach_end:
            continue
        can_reach_end.add(cur)
        for prev in reverse_edges.get(cur, []):
            dq.append(prev)

    _require(len(can_reach_end) == len(nodes_by_id), "存在无法到达 end 的节点")

    return ValidatedWorkflow(
        definition=definition,
        start_node_id=start_node_id,
        end_node_id=end_node_id,
        llm_node_id=llm_node_id,
        nodes_by_id=nodes_by_id,
        edges_by_source=dict(edges_by_source),
    )
