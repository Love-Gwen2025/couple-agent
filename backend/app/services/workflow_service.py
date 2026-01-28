from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_workflow import AgentWorkflow
from app.services.agent_service import AgentService
from app.workflow.definition import NodeTypeCatalogItem, WorkflowDefinition
from app.workflow.validation import validate_workflow_definition


def _default_workflow_definition() -> WorkflowDefinition:
    # MVP 默认流程：start → context → llm → end
    return WorkflowDefinition(
        schemaVersion=1,
        nodes=[
            {
                "id": "start",
                "type": "start",
                "label": "Start",
                "position": {"x": 80, "y": 140},
            },
            {
                "id": "context",
                "type": "context",
                "label": "Context",
                "config": {"enableHistory": True, "enableKnowledgeBase": True},
                "position": {"x": 320, "y": 140},
            },
            {
                "id": "llm",
                "type": "llm",
                "label": "LLM",
                "position": {"x": 560, "y": 140},
            },
            {
                "id": "end",
                "type": "end",
                "label": "End",
                "position": {"x": 800, "y": 140},
            },
        ],
        edges=[
            {"source": "start", "target": "context"},
            {"source": "context", "target": "llm"},
            {"source": "llm", "target": "end"},
        ],
    )


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_workflow(self, user_id: int, workflow_id: int) -> AgentWorkflow | None:
        stmt = select(AgentWorkflow).where(AgentWorkflow.id == workflow_id, AgentWorkflow.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def ensure_default_workflow(self, user_id: int, agent: Agent) -> AgentWorkflow:
        if agent.kind != "single":
            raise ValueError("仅 single Agent 支持 workflow")

        if agent.default_workflow_id:
            existing = await self.get_workflow(user_id, int(agent.default_workflow_id))
            if existing:
                return existing

        default_def = _default_workflow_definition()
        # 服务端落库前先校验（保证默认值永远合法）
        validate_workflow_definition(default_def)

        workflow = AgentWorkflow(
            user_id=user_id,
            agent_id=int(agent.id),
            schema_version=int(default_def.schemaVersion),
            definition_json=default_def.model_dump(),
        )
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)

        agent.default_workflow_id = int(workflow.id)
        await self.db.commit()
        await self.db.refresh(agent)

        return workflow

    async def get_agent_default_workflow(self, user_id: int, agent_id: int) -> tuple[Agent, AgentWorkflow]:
        agent_service = AgentService(self.db)
        agent = await agent_service.get_agent(user_id, agent_id)
        if not agent:
            raise ValueError("Agent 不存在或无权限")
        workflow = await self.ensure_default_workflow(user_id, agent)
        return agent, workflow

    async def update_agent_workflow(
        self,
        user_id: int,
        agent_id: int,
        definition: WorkflowDefinition,
    ) -> AgentWorkflow:
        agent_service = AgentService(self.db)
        agent = await agent_service.get_agent(user_id, agent_id)
        if not agent:
            raise ValueError("Agent 不存在或无权限")
        if agent.kind != "single":
            raise ValueError("仅 single Agent 支持 workflow")

        validate_workflow_definition(definition)

        workflow = AgentWorkflow(
            user_id=user_id,
            agent_id=agent_id,
            schema_version=int(definition.schemaVersion),
            definition_json=definition.model_dump(),
        )
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)

        agent.default_workflow_id = int(workflow.id)
        await self.db.commit()
        await self.db.refresh(agent)

        return workflow

    async def build_execution_spec(self, user_id: int, agent_id: int) -> dict:
        """
        构建会话执行快照（ExecutionSpec）。

        注意：此方法会确保 agent.default_workflow_id 存在（必要时创建默认 workflow 版本）。
        """
        agent_service = AgentService(self.db)
        cfg = await agent_service.get_agent_config(user_id, agent_id)
        agent: Agent = cfg["agent"]

        if agent.kind != "single":
            raise ValueError("仅 single Agent 支持 workflow 执行快照")

        workflow = await self.ensure_default_workflow(user_id, agent)

        return {
            "schemaVersion": 1,
            "agentId": int(agent.id),
            "agentName": agent.name,
            "agentKind": agent.kind,
            "userModelId": int(agent.user_model_id),
            "systemPrompt": agent.system_prompt,
            "toolRefs": list(cfg.get("toolRefs") or []),
            "knowledgeBaseIds": [int(x) for x in (cfg.get("knowledgeBaseIds") or [])],
            "workflowId": int(workflow.id),
            "workflowSchemaVersion": int(workflow.schema_version),
        }

    def list_node_types(self) -> list[NodeTypeCatalogItem]:
        return [
            NodeTypeCatalogItem(
                type="start",
                displayName="Start",
                description="入口节点（每个流程必须且只能有一个）",
                defaultConfig={},
            ),
            NodeTypeCatalogItem(
                type="router",
                displayName="Router",
                description="条件路由（仅该节点允许多出边）",
                defaultConfig={"strategy": "field", "field": "mode"},
                configSchema={
                    "type": "object",
                    "properties": {
                        "strategy": {"type": "string", "enum": ["field", "llm"]},
                        "field": {"type": "string"},
                        "prompt": {"type": "string"},
                        "defaultCase": {"type": "string"},
                    },
                },
            ),
            NodeTypeCatalogItem(
                type="context",
                displayName="Context",
                description="上下文检索（历史对话 + 知识库）",
                defaultConfig={"enableHistory": True, "enableKnowledgeBase": True},
                configSchema={
                    "type": "object",
                    "properties": {
                        "enableHistory": {"type": "boolean"},
                        "enableKnowledgeBase": {"type": "boolean"},
                    },
                },
            ),
            NodeTypeCatalogItem(
                type="llm",
                displayName="LLM",
                description="主生成节点（MVP：必须且只能一个）",
                defaultConfig={},
            ),
            NodeTypeCatalogItem(
                type="verify",
                displayName="Verify",
                description="校验/后处理（MVP：透传节点）",
                defaultConfig={},
            ),
            NodeTypeCatalogItem(
                type="end",
                displayName="End",
                description="结束节点（每个流程必须且只能有一个）",
                defaultConfig={},
            ),
        ]

