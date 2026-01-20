"""
用户模型管理 API

提供用户自定义模型配置的 CRUD 接口和测试接口。
"""

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.dependencies.auth import CurrentUser, get_current_user
from app.schema.base import ApiResult
from app.schema.user_model import (
    UserModelPayload,
    UserModelTestPayload,
    UserModelUpdatePayload,
    UserModelVo,
)
from app.services.user_model_service import UserModelService

router = APIRouter(prefix="/user/model", tags=["用户模型"])


def get_user_model_service(
    db: AsyncSession = Depends(get_db_session),
) -> UserModelService:
    """获取 UserModelService 实例"""
    return UserModelService(db)


@router.get("", response_model=ApiResult[list[UserModelVo]])
async def list_models(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserModelService = Depends(get_user_model_service),
) -> ApiResult[list[UserModelVo]]:
    """
    获取当前用户的所有模型配置
    """
    models = await service.list(current_user.id)
    return ApiResult.ok([UserModelVo(**m.to_vo()) for m in models])


@router.post("", response_model=ApiResult[UserModelVo])
async def create_model(
    payload: UserModelPayload,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserModelService = Depends(get_user_model_service),
) -> ApiResult[UserModelVo]:
    """
    添加新的模型配置
    """
    # 校验 custom 提供商必须有 base_url
    if payload.provider == "custom" and not payload.baseUrl:
        raise HTTPException(status_code=400, detail="custom 提供商必须填写 Base URL")

    model = await service.create(current_user.id, payload)
    return ApiResult.ok(UserModelVo(**model.to_vo()))


@router.put("/{model_id}", response_model=ApiResult[UserModelVo])
async def update_model(
    model_id: int,
    payload: UserModelUpdatePayload,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserModelService = Depends(get_user_model_service),
) -> ApiResult[UserModelVo]:
    """
    更新模型配置
    """
    model = await service.update(current_user.id, model_id, payload)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return ApiResult.ok(UserModelVo(**model.to_vo()))


@router.delete("/{model_id}", response_model=ApiResult[None])
async def delete_model(
    model_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserModelService = Depends(get_user_model_service),
) -> ApiResult[None]:
    """
    删除模型配置
    """
    success = await service.delete(current_user.id, model_id)
    if not success:
        raise HTTPException(status_code=404, detail="模型不存在")
    return ApiResult.ok(None)


@router.put("/{model_id}/default", response_model=ApiResult[None])
async def set_default_model(
    model_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: UserModelService = Depends(get_user_model_service),
) -> ApiResult[None]:
    """
    设置为默认模型
    """
    success = await service.set_default(current_user.id, model_id)
    if not success:
        raise HTTPException(status_code=404, detail="模型不存在")
    return ApiResult.ok(None)


@router.post("/test", response_model=ApiResult[dict])
async def test_model_connection(
    payload: UserModelTestPayload,
) -> ApiResult[dict]:
    """
    测试模型配置是否可用

    发送简单消息验证 API Key 连接
    """
    try:
        # 根据提供商创建临时模型实例
        model = _create_test_model(payload)

        # 发送测试消息
        response = await model.ainvoke([HumanMessage(content="Hi, just testing. Reply with 'OK'.")])

        # 返回成功结果
        return ApiResult.ok(
            {
                "success": True,
                "message": "连接成功",
                "response": str(response.content)[:100],  # 截取前 100 字符
            }
        )

    except Exception as e:
        logger.warning(f"模型测试失败: {e}")
        return ApiResult.ok(
            {
                "success": False,
                "message": f"连接失败: {str(e)}",
            }
        )


def _create_test_model(payload: UserModelTestPayload):
    """
    根据配置创建临时模型实例用于测试

    Args:
        payload: 测试配置

    Returns:
        LangChain ChatModel 实例
    """
    provider = payload.provider.lower()

    if provider == "gemini":
        # Google Gemini
        return ChatGoogleGenerativeAI(
            model=payload.modelCode,
            google_api_key=payload.apiKey,
            temperature=0.1,
        )
    elif provider == "openai":
        # OpenAI
        return ChatOpenAI(
            api_key=payload.apiKey,
            model=payload.modelCode,
            temperature=0.1,
            timeout=15,
        )
    elif provider == "deepseek":
        # DeepSeek (使用 OpenAI 兼容接口)
        return ChatOpenAI(
            api_key=payload.apiKey,
            base_url="https://api.deepseek.com",
            model=payload.modelCode,
            temperature=0.1,
            timeout=15,
        )
    elif provider == "custom":
        # 自定义中转站
        if not payload.baseUrl:
            raise ValueError("custom 提供商必须填写 Base URL")
        return ChatOpenAI(
            api_key=payload.apiKey,
            base_url=payload.baseUrl,
            model=payload.modelCode,
            temperature=0.1,
            timeout=15,
        )
    else:
        raise ValueError(f"不支持的提供商: {provider}")
