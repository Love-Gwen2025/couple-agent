from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

WorkflowNodeType = Literal["start", "router", "context", "llm", "verify", "end"]


class WorkflowPosition(BaseModel):
    x: float
    y: float


class WorkflowNode(BaseModel):
    id: str = Field(..., min_length=1, description="节点 ID（工作流内唯一）")
    type: WorkflowNodeType
    label: str | None = Field(default=None, description="节点显示名（UI 用）")
    config: dict[str, Any] = Field(default_factory=dict, description="节点配置（按 type 解释）")
    position: WorkflowPosition | None = Field(default=None, description="节点坐标（UI 用）")


class WorkflowEdge(BaseModel):
    id: str | None = Field(default=None, description="边 ID（可选，UI 用）")
    source: str = Field(..., min_length=1, description="源节点 ID")
    target: str = Field(..., min_length=1, description="目标节点 ID")
    case: str | None = Field(default=None, description="分支标签（仅 router 出边必填）")


class WorkflowDefinition(BaseModel):
    schemaVersion: int = Field(default=1, ge=1, description="Workflow definition schema 版本")
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)


class NodeTypeCatalogItem(BaseModel):
    type: WorkflowNodeType
    displayName: str
    description: str | None = None
    configSchema: dict[str, Any] | None = None
    defaultConfig: dict[str, Any] = Field(default_factory=dict)

