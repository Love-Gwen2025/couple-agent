from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_kb import AgentKnowledgeBase
from app.models.agent_member import AgentMember
from app.models.agent_tool import AgentTool
from app.models.knowledge_base import KnowledgeBase
from app.models.user_model import UserModel
from app.schema.agent import AgentPayload, AgentUpdatePayload
from app.services.tool_service import ToolService


class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tool_service = ToolService(db)

    async def list_agents(self, user_id: int) -> list[Agent]:
        stmt = select(Agent).where(Agent.user_id == user_id).order_by(Agent.create_time.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_agent(self, user_id: int, agent_id: int) -> Agent | None:
        stmt = select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _validate_user_model(self, user_id: int, user_model_id: int) -> None:
        stmt = select(UserModel).where(
            UserModel.id == user_model_id,
            UserModel.user_id == user_id,
        )
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        if not model:
            raise ValueError("绑定的模型不存在或无权限")
        if getattr(model, "status", 1) != 1:
            raise ValueError("绑定的模型已禁用")

    async def _validate_kbs(self, user_id: int, kb_ids: list[int]) -> None:
        if not kb_ids:
            return
        stmt = select(KnowledgeBase.id).where(
            KnowledgeBase.user_id == user_id, KnowledgeBase.id.in_(kb_ids)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        if len(rows) != len(set(kb_ids)):
            raise ValueError("存在不可访问的知识库")

    async def _validate_members(
        self, user_id: int, team_agent_id: int, member_ids: list[int]
    ) -> None:
        if not member_ids:
            raise ValueError("team Agent 必须至少包含 1 个成员 Agent")
        if team_agent_id in member_ids:
            raise ValueError("team Agent 不能包含自身")

        stmt = select(Agent).where(Agent.user_id == user_id, Agent.id.in_(member_ids))
        agents = list((await self.db.execute(stmt)).scalars().all())
        if len(agents) != len(set(member_ids)):
            raise ValueError("存在不可访问的成员 Agent")
        for a in agents:
            if a.kind != "single":
                raise ValueError("team Agent 的成员必须为 single Agent")
            if a.status != 1:
                raise ValueError("成员 Agent 已禁用")

    async def _replace_bindings(
        self,
        agent_id: int,
        tool_refs: list[str],
        kb_ids: list[int],
        member_ids: list[int] | None,
    ) -> None:
        await self.db.execute(delete(AgentTool).where(AgentTool.agent_id == agent_id))
        await self.db.execute(
            delete(AgentKnowledgeBase).where(AgentKnowledgeBase.agent_id == agent_id)
        )
        await self.db.execute(delete(AgentMember).where(AgentMember.team_agent_id == agent_id))

        for tool_ref in tool_refs:
            self.db.add(AgentTool(agent_id=agent_id, tool_ref=tool_ref))
        for kb_id in kb_ids:
            self.db.add(AgentKnowledgeBase(agent_id=agent_id, knowledge_base_id=kb_id))
        if member_ids:
            for idx, member_id in enumerate(member_ids):
                self.db.add(
                    AgentMember(team_agent_id=agent_id, member_agent_id=member_id, sort_order=idx)
                )

    async def create_agent(self, user_id: int, payload: AgentPayload) -> Agent:
        if payload.kind not in {"single", "team"}:
            raise ValueError("kind 仅支持 single/team")

        # SnowflakeId 类型已自动将 str 转为 int
        await self._validate_user_model(user_id, payload.userModelId)
        await self._validate_kbs(user_id, list(payload.knowledgeBaseIds))
        await self.tool_service.validate_tool_refs(user_id, payload.toolRefs)

        agent = Agent(
            user_id=user_id,
            kind=payload.kind,
            name=payload.name,
            description=payload.description,
            system_prompt=payload.systemPrompt,
            user_model_id=payload.userModelId,
            status=payload.status,
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)

        if payload.kind == "team":
            await self._validate_members(user_id, int(agent.id), list(payload.memberAgentIds))

        await self._replace_bindings(
            agent_id=int(agent.id),
            tool_refs=payload.toolRefs,
            kb_ids=list(payload.knowledgeBaseIds),
            member_ids=list(payload.memberAgentIds) if payload.kind == "team" else None,
        )
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def update_agent(
        self, user_id: int, agent_id: int, payload: AgentUpdatePayload
    ) -> Agent | None:
        agent = await self.get_agent(user_id, agent_id)
        if not agent:
            return None

        if payload.kind is not None:
            if payload.kind not in {"single", "team"}:
                raise ValueError("kind 仅支持 single/team")
            agent.kind = payload.kind

        if payload.name is not None:
            agent.name = payload.name
        if payload.description is not None:
            agent.description = payload.description
        if payload.systemPrompt is not None:
            agent.system_prompt = payload.systemPrompt
        if payload.status is not None:
            agent.status = payload.status
        if payload.userModelId is not None:
            await self._validate_user_model(user_id, payload.userModelId)
            agent.user_model_id = payload.userModelId

        await self.db.commit()

        tool_refs = (
            payload.toolRefs
            if payload.toolRefs is not None
            else await self._get_tool_refs(agent_id)
        )
        kb_ids = (
            list(payload.knowledgeBaseIds)
            if payload.knowledgeBaseIds is not None
            else await self._get_kb_ids(agent_id)
        )
        member_ids = (
            list(payload.memberAgentIds)
            if payload.memberAgentIds is not None
            else await self._get_member_ids(agent_id)
        )

        await self._validate_kbs(user_id, kb_ids)
        await self.tool_service.validate_tool_refs(user_id, tool_refs)
        if agent.kind == "team":
            await self._validate_members(user_id, agent_id, member_ids)
        else:
            member_ids = None

        await self._replace_bindings(
            agent_id=agent_id,
            tool_refs=tool_refs,
            kb_ids=kb_ids,
            member_ids=member_ids,
        )
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def delete_agent(self, user_id: int, agent_id: int) -> bool:
        agent = await self.get_agent(user_id, agent_id)
        if not agent:
            return False

        # 防止删除被 team 引用的成员
        stmt = select(AgentMember.id).where(AgentMember.member_agent_id == agent_id)
        in_use = (await self.db.execute(stmt)).scalar_one_or_none()
        if in_use:
            raise ValueError("该 Agent 正被 team Agent 引用，无法删除")

        await self.db.execute(delete(AgentTool).where(AgentTool.agent_id == agent_id))
        await self.db.execute(
            delete(AgentKnowledgeBase).where(AgentKnowledgeBase.agent_id == agent_id)
        )
        await self.db.execute(delete(AgentMember).where(AgentMember.team_agent_id == agent_id))
        await self.db.delete(agent)
        await self.db.commit()
        return True

    async def _get_tool_refs(self, agent_id: int) -> list[str]:
        stmt = select(AgentTool.tool_ref).where(AgentTool.agent_id == agent_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _get_kb_ids(self, agent_id: int) -> list[int]:
        stmt = select(AgentKnowledgeBase.knowledge_base_id).where(
            AgentKnowledgeBase.agent_id == agent_id
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def _get_member_ids(self, agent_id: int) -> list[int]:
        stmt = (
            select(AgentMember.member_agent_id)
            .where(AgentMember.team_agent_id == agent_id)
            .order_by(AgentMember.sort_order.asc(), AgentMember.create_time.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_agent_config(self, user_id: int, agent_id: int) -> dict:
        agent = await self.get_agent(user_id, agent_id)
        if not agent:
            raise ValueError("Agent 不存在或无权限")

        tool_refs = await self._get_tool_refs(agent_id)
        kb_ids = await self._get_kb_ids(agent_id)
        member_ids = await self._get_member_ids(agent_id) if agent.kind == "team" else []

        return {
            "agent": agent,
            "toolRefs": tool_refs,
            "knowledgeBaseIds": kb_ids,
            "memberAgentIds": member_ids,
        }
