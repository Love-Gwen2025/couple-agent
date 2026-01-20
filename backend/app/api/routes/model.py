"""
AI 模型配置接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.base import ApiResult
from app.schema.model import ModelVo
from app.services.user_model_service import UserModelService

router = APIRouter(prefix="/model", tags=["模型"])


async def get_optional_user(
    token: str | None = None,
    authorization: str | None = None,
) -> CurrentUser | None:
    """
    可选的用户认证

    未登录时返回 None 而非抛异常
    """
    from app.core.redis import get_redis

    if not token and not authorization:
        return None

    try:
        redis = await anext(get_redis())
        return await get_current_user(token, authorization, redis)
    except Exception:
        return None


@router.get("", response_model=ApiResult[list[ModelVo]])
async def list_models(
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResult[list[ModelVo]]:
    """
    返回可用模型列表

    包含:
    1. 系统默认模型 (DeepSeek-Chat)
    2. 用户自定义模型 (如已登录)
    """
    models: list[ModelVo] = []

    # 1. 系统默认模型 - DeepSeek Chat
    models.append(
        ModelVo(
            id=0,
            modelCode="deepseek-chat",
            modelName="DeepSeek Chat (默认)",
            provider="deepseek",
            isDefault=True,
            status=1,
        )
    )

    # 2. 用户自定义模型
    if current_user:
        service = UserModelService(db)
        user_models = await service.list(current_user.id)

        # 如果用户有自定义模型，检查是否有默认模型
        has_user_default = any(m.is_default for m in user_models)

        for idx, m in enumerate(user_models):
            # 如果用户设置了默认模型，系统默认模型不再是默认
            is_default = m.is_default
            if has_user_default and idx == 0:
                # 取消系统默认模型的默认状态
                models[0] = ModelVo(
                    id=0,
                    modelCode="deepseek-chat",
                    modelName="DeepSeek Chat (系统)",
                    provider="deepseek",
                    isDefault=False,
                    status=1,
                )

            models.append(
                ModelVo(
                    id=int(m.id) if m.id else idx + 1,
                    modelCode=m.model_code,
                    modelName=m.model_name,
                    provider=m.provider,
                    isDefault=is_default,
                    status=m.status,
                )
            )

    return ApiResult.ok(models)


@router.get("/default", response_model=ApiResult[ModelVo])
async def get_default_model(
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResult[ModelVo]:
    """
    返回默认模型
    """
    result = await list_models(current_user, db)
    models = result.data or []
    default_model = next((m for m in models if m.isDefault), models[0] if models else None)
    if default_model is None:
        return ApiResult.error("MODEL-404", "无可用模型")
    return ApiResult.ok(default_model)
