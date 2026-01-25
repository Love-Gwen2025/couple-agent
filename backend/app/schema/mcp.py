from pydantic import BaseModel, Field

from app.schema.base import SnowflakeId


class McpServerVo(BaseModel):
    id: SnowflakeId
    userId: SnowflakeId
    name: str
    url: str
    status: int
    hasHeaders: bool = False
    createTime: str | None = None
    updateTime: str | None = None


class McpServerPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    status: int = Field(default=1, description="状态: 0=禁用 1=启用")
    headers: dict[str, str] | None = Field(default=None, description="可选的鉴权头")


class McpServerUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    status: int | None = Field(default=None, description="状态: 0=禁用 1=启用")
    headers: dict[str, str] | None = Field(default=None, description="可选的鉴权头（覆盖）")


class McpToolVo(BaseModel):
    id: SnowflakeId
    serverId: SnowflakeId
    name: str
    description: str | None = None
    inputSchema: dict | None = None
    enabled: bool
    createTime: str | None = None
    updateTime: str | None = None


class McpToolUpdatePayload(BaseModel):
    enabled: bool = Field(..., description="是否启用")


class McpToolTestPayload(BaseModel):
    arguments: dict = Field(default_factory=dict, description="工具入参（JSON）")


class McpToolTestResult(BaseModel):
    success: bool
    isError: bool = False
    data: dict | list | str | int | float | bool | None = None
    text: str | None = None

