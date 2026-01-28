"""
Agent 管理 API

提供用户自定义 Agent 的 CRUD 与配置绑定能力。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.agent import AgentPayload, AgentUpdatePayload, AgentVo
from app.schema.base import ApiResult
from app.schema.workflow import AgentWorkflowUpdatePayload, AgentWorkflowVo
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.workflow.definition import WorkflowDefinition

router = APIRouter(prefix="/agents", tags=["Agent"])


def get_agent_service(db: AsyncSession = Depends(get_db_session)) -> AgentService:
    return AgentService(db)


def get_workflow_service(db: AsyncSession = Depends(get_db_session)) -> WorkflowService:
    return WorkflowService(db)


@router.get("", response_model=ApiResult[list[AgentVo]])
async def list_agents(
    current: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> ApiResult[list[AgentVo]]:
    agents = await service.list_agents(current.id)
    # 返回不含 bindings 的轻量列表（前端详情页再拉取）
    records = [AgentVo(**a.to_vo(), toolRefs=[], knowledgeBaseIds=[], memberAgentIds=[]) for a in agents]
    return ApiResult.ok(records)


@router.get("/{agent_id}", response_model=ApiResult[AgentVo])
async def get_agent_detail(
    agent_id: str,
    current: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> ApiResult[AgentVo]:
    cfg = await service.get_agent_config(current.id, int(agent_id))
    agent = cfg["agent"]
    vo = AgentVo(
        **agent.to_vo(),
        toolRefs=cfg["toolRefs"],
        knowledgeBaseIds=cfg["knowledgeBaseIds"],
        memberAgentIds=cfg["memberAgentIds"],
    )
    return ApiResult.ok(vo)


@router.post("", response_model=ApiResult[AgentVo])
async def create_agent(
    payload: AgentPayload,
    current: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> ApiResult[AgentVo]:
    try:
        agent = await service.create_agent(current.id, payload)
        cfg = await service.get_agent_config(current.id, int(agent.id))
        vo = AgentVo(
            **agent.to_vo(),
            toolRefs=cfg["toolRefs"],
            knowledgeBaseIds=cfg["knowledgeBaseIds"],
            memberAgentIds=cfg["memberAgentIds"],
        )
        return ApiResult.ok(vo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{agent_id}", response_model=ApiResult[AgentVo])
async def update_agent(
    agent_id: str,
    payload: AgentUpdatePayload,
    current: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> ApiResult[AgentVo]:
    try:
        agent = await service.update_agent(current.id, int(agent_id), payload)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent 不存在")
        cfg = await service.get_agent_config(current.id, int(agent.id))
        vo = AgentVo(
            **agent.to_vo(),
            toolRefs=cfg["toolRefs"],
            knowledgeBaseIds=cfg["knowledgeBaseIds"],
            memberAgentIds=cfg["memberAgentIds"],
        )
        return ApiResult.ok(vo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{agent_id}", response_model=ApiResult[None])
async def delete_agent(
    agent_id: str,
    current: CurrentUser = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> ApiResult[None]:
    try:
        success = await service.delete_agent(current.id, int(agent_id))
        if not success:
            raise HTTPException(status_code=404, detail="Agent 不存在")
        return ApiResult.ok(None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{agent_id}/workflow", response_model=ApiResult[AgentWorkflowVo])
async def get_agent_workflow(
    agent_id: str,
    current: CurrentUser = Depends(get_current_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> ApiResult[AgentWorkflowVo]:
    try:
        _, wf = await workflow_service.get_agent_default_workflow(current.id, int(agent_id))
        definition = WorkflowDefinition(**(wf.definition_json or {}))
        return ApiResult.ok(
            AgentWorkflowVo(
                workflowId=wf.id,
                schemaVersion=wf.schema_version,
                definition=definition,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{agent_id}/workflow", response_model=ApiResult[AgentWorkflowVo])
async def update_agent_workflow(
    agent_id: str,
    payload: AgentWorkflowUpdatePayload,
    current: CurrentUser = Depends(get_current_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> ApiResult[AgentWorkflowVo]:
    try:
        wf = await workflow_service.update_agent_workflow(
            current.id, int(agent_id), payload.definition
        )
        definition = WorkflowDefinition(**(wf.definition_json or {}))
        return ApiResult.ok(
            AgentWorkflowVo(
                workflowId=wf.id,
                schemaVersion=wf.schema_version,
                definition=definition,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
