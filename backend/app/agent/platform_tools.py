from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import ConfigDict, Field, create_model
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mcp_service import McpService
from app.services.tool_service import (
    BUILTIN_TOOL_REF_PREFIX,
    MCP_TOOL_REF_PREFIX,
    ToolService,
    get_builtin_tools,
)


def _python_type_from_json_schema(schema: dict[str, Any]) -> Any:
    schema_type = schema.get("type")
    if schema_type == "string":
        return str
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "array":
        return list[Any]
    if schema_type == "object":
        return dict[str, Any]
    # fallback（包含 anyOf/oneOf 等复杂情况）
    return Any


def _build_args_model(model_name: str, input_schema: dict[str, Any] | None):
    if not input_schema:
        # 无 schema 时允许任意字段，避免工具不可调用
        return create_model(  # type: ignore[call-arg]
            model_name,
            __config__=ConfigDict(extra="allow"),
        )

    schema_type = input_schema.get("type")
    if schema_type != "object":
        # 非 object 的 schema：统一收敛到 arguments 字段
        return create_model(  # type: ignore[call-arg]
            model_name,
            __config__=ConfigDict(extra="allow"),
            arguments=(Any, Field(description="MCP tool arguments")),
        )

    props = input_schema.get("properties", {}) or {}
    required = set(input_schema.get("required", []) or [])

    fields: dict[str, tuple[Any, Field]] = {}
    for prop_name, prop_schema in props.items():
        typ = _python_type_from_json_schema(prop_schema or {})
        desc = (prop_schema or {}).get("description")
        if prop_name in required:
            fields[prop_name] = (typ, Field(..., description=desc))
        else:
            fields[prop_name] = (typ | None, Field(default=None, description=desc))

    return create_model(  # type: ignore[call-arg]
        model_name,
        __config__=ConfigDict(extra="allow"),
        **fields,
    )


async def build_tools_for_tool_refs(
    db: AsyncSession, user_id: int, tool_refs: list[str]
) -> tuple[list[BaseTool], dict[str, dict[str, str]]]:
    """
    将 toolRefs 转换为 LangChain 工具列表，并返回 tool.name -> 元信息映射。

    返回的元信息用于 SSE 事件显示（toolRef/displayName）。
    """
    tool_service = ToolService(db)
    await tool_service.validate_tool_refs(user_id, tool_refs)

    builtin_map = get_builtin_tools()
    tools: list[BaseTool] = []
    name_meta: dict[str, dict[str, str]] = {}

    for tool_ref in tool_refs:
        if tool_ref.startswith(BUILTIN_TOOL_REF_PREFIX):
            tool = builtin_map[tool_ref]
            tools.append(tool)
            name_meta[tool.name] = {"toolRef": tool_ref, "displayName": tool.name}
            continue

        if tool_ref.startswith(MCP_TOOL_REF_PREFIX):
            tool_id = int(tool_ref[len(MCP_TOOL_REF_PREFIX) :])
            mcp_server, mcp_tool = await tool_service.get_mcp_tool(user_id, tool_id)
            mcp_service = McpService(db)
            headers = await mcp_service._get_headers(mcp_server)  # noqa: SLF001

            llm_tool_name = f"mcp_tool_{mcp_tool.id}"
            args_model = _build_args_model(f"McpToolArgs_{mcp_tool.id}", mcp_tool.input_schema)

            # 使用工厂函数捕获当前循环的值，避免闭包陷阱 (S1515)
            def _make_mcp_caller(server_url: str, hdrs: dict, tool_name: str):
                async def _call(**kwargs):
                    try:
                        from fastmcp import Client
                        from fastmcp.client.transports import StreamableHttpTransport
                    except Exception as exc:
                        raise RuntimeError("缺少 fastmcp 依赖，请先安装 fastmcp") from exc

                    transport = StreamableHttpTransport(server_url, headers=hdrs)
                    async with Client(transport=transport, timeout=30.0) as client:
                        result = await client.call_tool(tool_name, kwargs)
                    return await tool_service.format_mcp_tool_call_result(result)

                return _call

            _call_mcp = _make_mcp_caller(mcp_server.url, headers, mcp_tool.name)

            tool = StructuredTool.from_function(
                name=llm_tool_name,
                description=(mcp_tool.description or "").strip()
                or f"MCP Tool: {mcp_server.name}:{mcp_tool.name}",
                coroutine=_call_mcp,
                args_schema=args_model,
            )

            tools.append(tool)
            name_meta[tool.name] = {
                "toolRef": tool_ref,
                "displayName": f"{mcp_server.name}:{mcp_tool.name}",
            }
            continue

        raise ValueError(f"未知 tool_ref: {tool_ref}")

    return tools, name_meta
