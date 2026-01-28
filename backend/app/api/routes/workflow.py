"""
Workflow 管理 API

- NodeType catalog（用于前端渲染节点面板与配置表单）
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.base import ApiResult
from app.workflow.definition import NodeTypeCatalogItem
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflow", tags=["Workflow"])


def get_workflow_service(db: AsyncSession = Depends(get_db_session)) -> WorkflowService:
    return WorkflowService(db)


@router.get("/node-types", response_model=ApiResult[list[NodeTypeCatalogItem]])
async def list_node_types(
    _: CurrentUser = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> ApiResult[list[NodeTypeCatalogItem]]:
    return ApiResult.ok(service.list_node_types())

