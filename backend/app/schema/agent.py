from pydantic import BaseModel, Field

from app.schema.base import SnowflakeId


class AgentVo(BaseModel):
    id: SnowflakeId
    userId: SnowflakeId
    kind: str
    name: str
    description: str | None = None
    systemPrompt: str | None = None
    userModelId: SnowflakeId
    status: int
    toolRefs: list[str] = Field(default_factory=list)
    knowledgeBaseIds: list[SnowflakeId] = Field(default_factory=list)
    memberAgentIds: list[SnowflakeId] = Field(default_factory=list)
    createTime: str | None = None
    updateTime: str | None = None


class AgentPayload(BaseModel):
    kind: str = Field(default="single", description="Agent 类型: single/team")
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    systemPrompt: str | None = None
    userModelId: SnowflakeId = Field(..., description="绑定的用户模型 ID")
    status: int = Field(default=1, description="状态: 0=禁用 1=启用")
    toolRefs: list[str] = Field(default_factory=list, description="绑定的工具 ToolRef 列表")
    knowledgeBaseIds: list[SnowflakeId] = Field(
        default_factory=list, description="绑定的知识库 ID 列表"
    )
    memberAgentIds: list[SnowflakeId] = Field(
        default_factory=list, description="team Agent 的成员 Agent ID 列表"
    )


class AgentUpdatePayload(BaseModel):
    kind: str | None = Field(default=None, description="Agent 类型: single/team")
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    systemPrompt: str | None = None
    userModelId: SnowflakeId | None = Field(default=None, description="绑定的用户模型 ID")
    status: int | None = Field(default=None, description="状态: 0=禁用 1=启用")
    toolRefs: list[str] | None = Field(default=None, description="绑定的工具 ToolRef 列表")
    knowledgeBaseIds: list[SnowflakeId] | None = Field(
        default=None, description="绑定的知识库 ID 列表"
    )
    memberAgentIds: list[SnowflakeId] | None = Field(
        default=None, description="team Agent 的成员 Agent ID 列表"
    )
