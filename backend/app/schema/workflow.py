from pydantic import BaseModel, Field

from app.schema.base import SnowflakeId
from app.workflow.definition import NodeTypeCatalogItem, WorkflowDefinition


class NodeTypeCatalogResponse(BaseModel):
    items: list[NodeTypeCatalogItem] = Field(default_factory=list)


class AgentWorkflowVo(BaseModel):
    workflowId: SnowflakeId
    schemaVersion: int
    definition: WorkflowDefinition


class AgentWorkflowUpdatePayload(BaseModel):
    definition: WorkflowDefinition

