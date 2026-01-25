import json
from collections.abc import Sequence
from typing import Any

from langchain_core.tools import BaseTool
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_server import McpServer
from app.models.mcp_tool import McpTool
from app.schema.tool import ToolVo

BUILTIN_TOOL_REF_PREFIX = "builtin:"
MCP_TOOL_REF_PREFIX = "mcp:"


def get_builtin_tools() -> dict[str, BaseTool]:
    """
    返回内置工具映射：tool_ref -> tool
    """
    from app.tools import AVAILABLE_TOOLS
    from app.tools.rag_tool import rag_search
    from app.tools.tavily_tool import web_search

    tools: list[BaseTool] = [
        *list(AVAILABLE_TOOLS),
        rag_search,
        web_search,
    ]

    return {f"{BUILTIN_TOOL_REF_PREFIX}{t.name}": t for t in tools}


class ToolService:
    """
    工具目录服务：统一管理内置工具与 MCP 工具（同一层级）。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tools(self, user_id: int) -> list[ToolVo]:
        builtin = get_builtin_tools()
        result: list[ToolVo] = []

        for tool_ref, tool in builtin.items():
            result.append(
                ToolVo(
                    toolRef=tool_ref,
                    type="builtin",
                    name=tool.name,
                    displayName=tool.name,
                    description=getattr(tool, "description", None),
                    enabled=True,
                    inputSchema=getattr(tool, "args_schema", None).model_json_schema()
                    if getattr(tool, "args_schema", None)
                    else None,
                )
            )

        stmt = (
            select(McpTool, McpServer)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .where(McpServer.user_id == user_id)
        )
        rows = (await self.db.execute(stmt)).all()
        for mcp_tool, mcp_server in rows:
            result.append(
                ToolVo(
                    toolRef=f"{MCP_TOOL_REF_PREFIX}{mcp_tool.id}",
                    type="mcp",
                    name=mcp_tool.name,
                    displayName=f"{mcp_server.name}:{mcp_tool.name}",
                    description=mcp_tool.description,
                    enabled=bool(mcp_tool.enabled) and mcp_server.status == 1,
                    inputSchema=mcp_tool.input_schema,
                )
            )

        return result

    async def validate_tool_refs(self, user_id: int, tool_refs: Sequence[str]) -> None:
        """
        校验工具引用是否存在且属于当前用户（MCP）。
        """
        builtin = get_builtin_tools()

        for tool_ref in tool_refs:
            if tool_ref.startswith(BUILTIN_TOOL_REF_PREFIX):
                if tool_ref not in builtin:
                    raise ValueError(f"未知内置工具: {tool_ref}")
                continue

            if tool_ref.startswith(MCP_TOOL_REF_PREFIX):
                tool_id_str = tool_ref[len(MCP_TOOL_REF_PREFIX) :]
                try:
                    tool_id = int(tool_id_str)
                except ValueError as exc:
                    raise ValueError(f"非法 MCP tool_ref: {tool_ref}") from exc

                stmt = (
                    select(McpTool, McpServer)
                    .join(McpServer, McpServer.id == McpTool.server_id)
                    .where(McpTool.id == tool_id, McpServer.user_id == user_id)
                )
                row = (await self.db.execute(stmt)).first()
                if not row:
                    raise ValueError(f"MCP 工具不存在或无权限: {tool_ref}")
                mcp_tool, mcp_server = row
                if mcp_server.status != 1:
                    raise ValueError(f"MCP Server 已禁用: server_id={mcp_server.id}")
                if not mcp_tool.enabled:
                    raise ValueError(f"MCP 工具已禁用: {tool_ref}")
                continue

            raise ValueError(f"未知 tool_ref: {tool_ref}")

    async def get_mcp_tool(self, user_id: int, tool_id: int) -> tuple[McpServer, McpTool]:
        stmt = (
            select(McpTool, McpServer)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .where(McpTool.id == tool_id, McpServer.user_id == user_id)
        )
        row = (await self.db.execute(stmt)).first()
        if not row:
            raise ValueError("MCP 工具不存在或无权限")
        mcp_tool, mcp_server = row
        return mcp_server, mcp_tool

    async def format_mcp_tool_call_result(self, call_result: Any) -> str:
        """
        将 FastMCP 的 CallToolResult 转为可写入对话的字符串。
        """
        try:
            if getattr(call_result, "is_error", False):
                content = getattr(call_result, "content", None) or []
                texts = []
                for item in content:
                    text = getattr(item, "text", None)
                    if text:
                        texts.append(text)
                return "\n".join(texts) if texts else "MCP 工具调用失败"

            structured_content = getattr(call_result, "structured_content", None)
            if structured_content is not None:
                return json.dumps(structured_content, ensure_ascii=False, default=str)

            data = getattr(call_result, "data", None)
            if data is not None:
                if isinstance(data, str):
                    return data
                return json.dumps(data, ensure_ascii=False, default=str)

            content = getattr(call_result, "content", None) or []
            texts = []
            for item in content:
                text = getattr(item, "text", None)
                if text:
                    texts.append(text)
            return "\n".join(texts) if texts else ""
        except Exception as exc:
            logger.warning(f"Failed to format MCP result: {exc}")
            return str(call_result)
