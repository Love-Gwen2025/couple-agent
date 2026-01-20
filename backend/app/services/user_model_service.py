"""
用户模型管理服务

提供用户自定义模型配置的 CRUD 操作。
"""

from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_api_key, encrypt_api_key
from app.models.user_model import UserModel
from app.schema.user_model import UserModelPayload, UserModelUpdatePayload
from app.utils.snowflake import generate_id


class UserModelService:
    """
    用户模型管理服务

    职责：
    1. CRUD 用户自定义模型配置
    2. 管理用户默认模型
    3. API Key 加密/解密
    """

    def __init__(self, db: AsyncSession):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def list(self, user_id: int) -> list[UserModel]:
        """
        获取用户的所有模型配置

        Args:
            user_id: 用户 ID

        Returns:
            用户模型列表
        """
        stmt = (
            select(UserModel)
            .where(UserModel.user_id == user_id)
            .order_by(UserModel.is_default.desc(), UserModel.create_time.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, user_id: int, model_id: int) -> UserModel | None:
        """
        获取单个模型配置

        Args:
            user_id: 用户 ID
            model_id: 模型 ID

        Returns:
            模型配置或 None
        """
        stmt = select(UserModel).where(
            UserModel.id == model_id,
            UserModel.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_decrypted_key(self, user_id: int, model_id: int) -> UserModel | None:
        """
        获取模型配置并解密 API Key

        用于实际调用 AI 时获取明文 API Key

        Args:
            user_id: 用户 ID
            model_id: 模型 ID

        Returns:
            模型配置（api_key 已解密）或 None
        """
        model = await self.get(user_id, model_id)
        if model:
            # 解密 API Key
            model.api_key = decrypt_api_key(model.api_key)
        return model

    async def create(self, user_id: int, payload: UserModelPayload) -> UserModel:
        """
        创建用户模型配置

        Args:
            user_id: 用户 ID
            payload: 模型配置数据

        Returns:
            创建的模型实体
        """
        # 加密 API Key
        encrypted_key = encrypt_api_key(payload.apiKey)

        model = UserModel(
            id=generate_id(),
            user_id=user_id,
            model_name=payload.modelName,
            provider=payload.provider,
            model_code=payload.modelCode,
            api_key=encrypted_key,
            base_url=payload.baseUrl,
            temperature=Decimal(str(payload.temperature)),
            timeout=payload.timeout,
            # 高级参数
            top_p=Decimal(str(payload.topP)) if payload.topP is not None else None,
            max_tokens=payload.maxTokens,
            top_k=payload.topK,
            is_default=False,
            status=1,
        )

        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def update(
        self, user_id: int, model_id: int, payload: UserModelUpdatePayload
    ) -> UserModel | None:
        """
        更新模型配置

        Args:
            user_id: 用户 ID
            model_id: 模型 ID
            payload: 更新数据

        Returns:
            更新后的模型或 None
        """
        model = await self.get(user_id, model_id)
        if not model:
            return None

        # 更新字段（只更新非 None 的值）
        if payload.modelName is not None:
            model.model_name = payload.modelName
        if payload.provider is not None:
            model.provider = payload.provider
        if payload.modelCode is not None:
            model.model_code = payload.modelCode
        if payload.apiKey is not None:
            # 加密新的 API Key
            model.api_key = encrypt_api_key(payload.apiKey)
        if payload.baseUrl is not None:
            model.base_url = payload.baseUrl
        if payload.temperature is not None:
            model.temperature = Decimal(str(payload.temperature))
        if payload.timeout is not None:
            model.timeout = payload.timeout
        # 高级参数
        if payload.topP is not None:
            model.top_p = Decimal(str(payload.topP))
        if payload.maxTokens is not None:
            model.max_tokens = payload.maxTokens
        if payload.topK is not None:
            model.top_k = payload.topK

        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def delete(self, user_id: int, model_id: int) -> bool:
        """
        删除模型配置

        Args:
            user_id: 用户 ID
            model_id: 模型 ID

        Returns:
            是否删除成功
        """
        model = await self.get(user_id, model_id)
        if not model:
            return False

        await self.db.delete(model)
        await self.db.commit()
        return True

    async def set_default(self, user_id: int, model_id: int) -> bool:
        """
        设置默认模型

        先取消该用户所有模型的默认状态，再设置指定模型为默认

        Args:
            user_id: 用户 ID
            model_id: 模型 ID

        Returns:
            是否设置成功
        """
        # 检查模型是否存在
        model = await self.get(user_id, model_id)
        if not model:
            return False

        # 取消所有默认
        await self.db.execute(
            update(UserModel).where(UserModel.user_id == user_id).values(is_default=False)
        )

        # 设置新默认
        model.is_default = True
        await self.db.commit()
        return True

    async def get_default(self, user_id: int) -> UserModel | None:
        """
        获取用户默认模型

        Args:
            user_id: 用户 ID

        Returns:
            默认模型或 None
        """
        stmt = select(UserModel).where(
            UserModel.user_id == user_id,
            UserModel.is_default == True,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_with_decrypted_key(self, user_id: int) -> UserModel | None:
        """
        获取用户默认模型并解密 API Key

        Args:
            user_id: 用户 ID

        Returns:
            默认模型（api_key 已解密）或 None
        """
        model = await self.get_default(user_id)
        if model:
            model.api_key = decrypt_api_key(model.api_key)
        return model
