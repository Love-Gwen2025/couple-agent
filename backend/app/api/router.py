from fastapi import APIRouter

from app.api.routes import (
    agent,
    branch,
    chat,
    conversation,
    knowledge,
    mcp,
    model,
    tool,
    user,
    user_model,
    workflow,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(user.router)
api_router.include_router(conversation.router)
api_router.include_router(chat.router)
api_router.include_router(model.router)
api_router.include_router(user_model.router)  # 用户模型管理路由
api_router.include_router(branch.router)  # 分支管理路由
api_router.include_router(knowledge.router)  # 知识库管理路由
api_router.include_router(agent.router)  # Agent 管理
api_router.include_router(tool.router)  # Tool 目录
api_router.include_router(mcp.router)  # MCP 管理
api_router.include_router(workflow.router)  # Workflow（节点编排）
