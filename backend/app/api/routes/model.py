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

    只返回用户自定义模型（系统不再内置默认模型）
    """
    models: list[ModelVo] = []

    # 用户自定义模型
    if current_user:
        service = UserModelService(db)
        user_models = await service.list(current_user.id)

        for m in user_models:
            models.append(
                ModelVo(
                    id=m.id or 0,
                    modelCode=m.model_code,
                    modelName=m.model_name,
                    provider=m.provider,
                    isDefault=m.is_default,
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
