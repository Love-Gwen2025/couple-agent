"""
Tool 目录 API

统一对外暴露内置工具与用户 MCP 工具。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.base import ApiResult
from app.schema.tool import ToolVo
from app.services.tool_service import ToolService

router = APIRouter(prefix="/tools", tags=["Tools"])


def get_tool_service(db: AsyncSession = Depends(get_db_session)) -> ToolService:
    return ToolService(db)


@router.get("", response_model=ApiResult[list[ToolVo]])
async def list_tools(
    current: CurrentUser = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> ApiResult[list[ToolVo]]:
    tools = await service.list_tools(current.id)
    return ApiResult.ok(tools)

