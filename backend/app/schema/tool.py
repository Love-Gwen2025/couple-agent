from pydantic import BaseModel, Field


class ToolVo(BaseModel):
    toolRef: str
    type: str = Field(..., description="builtin/mcp")
    name: str
    displayName: str | None = None
    description: str | None = None
    enabled: bool = True
    inputSchema: dict | None = None

