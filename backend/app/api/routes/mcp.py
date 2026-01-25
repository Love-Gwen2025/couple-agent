"""
MCP 管理 API

提供 MCP Server 注册、工具同步、启用/禁用与测试调用。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.base import ApiResult
from app.schema.mcp import (
    McpServerPayload,
    McpServerUpdatePayload,
    McpServerVo,
    McpToolTestPayload,
    McpToolTestResult,
    McpToolUpdatePayload,
    McpToolVo,
)
from app.services.mcp_service import McpService
from app.services.tool_service import ToolService

router = APIRouter(prefix="/mcp", tags=["MCP"])


def get_mcp_service(db: AsyncSession = Depends(get_db_session)) -> McpService:
    return McpService(db)


def get_tool_service(db: AsyncSession = Depends(get_db_session)) -> ToolService:
    return ToolService(db)


@router.get("/servers", response_model=ApiResult[list[McpServerVo]])
async def list_servers(
    current: CurrentUser = Depends(get_current_user),
    service: McpService = Depends(get_mcp_service),
) -> ApiResult[list[McpServerVo]]:
    servers = await service.list_servers(current.id)
    records: list[McpServerVo] = []
    for s in servers:
        records.append(
            McpServerVo(
                **s.to_vo(),
                hasHeaders=bool(s.headers_encrypted),
            )
        )
    return ApiResult.ok(records)


@router.post("/servers", response_model=ApiResult[McpServerVo])
async def create_server(
    payload: McpServerPayload,
    current: CurrentUser = Depends(get_current_user),
    service: McpService = Depends(get_mcp_service),
) -> ApiResult[McpServerVo]:
    try:
        server = await service.create_server(current.id, payload)
        return ApiResult.ok(McpServerVo(**server.to_vo(), hasHeaders=bool(server.headers_encrypted)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/servers/{server_id}", response_model=ApiResult[McpServerVo])
async def update_server(
    server_id: str,
    payload: McpServerUpdatePayload,
    current: CurrentUser = Depends(get_current_user),
    service: McpService = Depends(get_mcp_service),
) -> ApiResult[McpServerVo]:
    try:
        server = await service.update_server(current.id, int(server_id), payload)
        if not server:
            raise HTTPException(status_code=404, detail="MCP Server 不存在")
        return ApiResult.ok(McpServerVo(**server.to_vo(), hasHeaders=bool(server.headers_encrypted)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/servers/{server_id}", response_model=ApiResult[None])
async def delete_server(
    server_id: str,
    current: CurrentUser = Depends(get_current_user),
    service: McpService = Depends(get_mcp_service),
) -> ApiResult[None]:
    success = await service.delete_server(current.id, int(server_id))
    if not success:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    return ApiResult.ok(None)


@router.post("/servers/{server_id}/sync", response_model=ApiResult[dict])
async def sync_tools(
    server_id: str,
    current: CurrentUser = Depends(get_current_user),
    service: McpService = Depends(get_mcp_service),
) -> ApiResult[dict]:
    try:
        count = await service.sync_tools(current.id, int(server_id))
        return ApiResult.ok({"count": count})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tools", response_model=ApiResult[list[McpToolVo]])
async def list_mcp_tools(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResult[list[McpToolVo]]:
    """
    列出当前用户所有 MCP tools（跨 server）。
    """
    from sqlalchemy import select

    from app.models.mcp_server import McpServer
    from app.models.mcp_tool import McpTool

    stmt = (
        select(McpTool)
        .join(McpServer, McpServer.id == McpTool.server_id)
        .where(McpServer.user_id == current.id)
        .order_by(McpTool.update_time.desc())
    )
    tools = list((await db.execute(stmt)).scalars().all())
    return ApiResult.ok([McpToolVo(**t.to_vo()) for t in tools])


@router.put("/tools/{tool_id}", response_model=ApiResult[McpToolVo])
async def update_mcp_tool(
    tool_id: str,
    payload: McpToolUpdatePayload,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResult[McpToolVo]:
    from sqlalchemy import select

    from app.models.mcp_server import McpServer
    from app.models.mcp_tool import McpTool

    stmt = (
        select(McpTool, McpServer)
        .join(McpServer, McpServer.id == McpTool.server_id)
        .where(McpTool.id == int(tool_id), McpServer.user_id == current.id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="MCP Tool 不存在")
    mcp_tool, _server = row
    mcp_tool.enabled = payload.enabled
    await db.commit()
    await db.refresh(mcp_tool)
    return ApiResult.ok(McpToolVo(**mcp_tool.to_vo()))


@router.post("/tools/{tool_id}/test", response_model=ApiResult[McpToolTestResult])
async def test_mcp_tool(
    tool_id: str,
    payload: McpToolTestPayload,
    current: CurrentUser = Depends(get_current_user),
    tool_service: ToolService = Depends(get_tool_service),
) -> ApiResult[McpToolTestResult]:
    try:
        mcp_server, mcp_tool = await tool_service.get_mcp_tool(current.id, int(tool_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if mcp_server.status != 1:
        raise HTTPException(status_code=400, detail="MCP Server 已禁用")
    if not mcp_tool.enabled:
        raise HTTPException(status_code=400, detail="MCP Tool 已禁用")

    try:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
    except Exception as exc:
        raise HTTPException(status_code=500, detail="缺少 fastmcp 依赖，请先安装 fastmcp") from exc

    # headers 解密复用 McpService 逻辑（避免重复实现）
    from app.services.mcp_service import McpService

    # 这里无法通过 Depends 注入同一个 db，直接新建 service 并复用 db session
    mcp_service = McpService(tool_service.db)
    headers = await mcp_service._get_headers(mcp_server)  # noqa: SLF001

    transport = StreamableHttpTransport(mcp_server.url, headers=headers)
    async with Client(transport=transport, timeout=30.0) as client:
        result = await client.call_tool(mcp_tool.name, payload.arguments or {})

    text = await tool_service.format_mcp_tool_call_result(result)
    return ApiResult.ok(
        McpToolTestResult(
            success=not bool(getattr(result, "is_error", False)),
            isError=bool(getattr(result, "is_error", False)),
            data=getattr(result, "structured_content", None),
            text=text,
        )
    )

