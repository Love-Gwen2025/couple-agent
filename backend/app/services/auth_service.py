from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.models.user import User
from app.utils.jwt_token import create_access_token
from app.utils.password import hash_password, verify_password
from app.utils.session_store import SessionStore


class AuthService:
    """
    1. 处理用户注册、登录与注销的核心逻辑。
    """

    def __init__(self, db: AsyncSession, store: SessionStore, settings: Settings):
        self.db = db
        self.store = store
        self.settings = settings

    async def register(self, payload: dict) -> int:
        """
        1. 创建用户，检查重复并存储 bcrypt 哈希。
        """
        user_code = payload.get("userCode")
        # 1. 查询用户是否已存在
        query = await self.db.execute(select(User).where(User.user_code == user_code))
        existing = query.scalar_one_or_none()
        if existing:
            raise ValueError("用户已存在")
        # 2. 生成密码哈希并写入
        hashed = hash_password(payload["userPassword"])
        user = User(
            user_code=user_code,
            user_name=payload.get("userName") or user_code,
            user_password=hashed,
            user_phone=payload.get("userPhone"),
            address=payload.get("address"),
            user_sex=payload.get("userSex", 0),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user.id

    async def login(self, payload: dict) -> str:
        user_code = payload.get("userCode")
        # 1. 拉取用户信息
        query = await self.db.execute(select(User).where(User.user_code == user_code))
        user = query.scalar_one_or_none()
        # 2. 统一错误消息，避免泄露用户是否存在
        if user is None or not verify_password(payload.get("userPassword"), user.user_password):
            raise ValueError("账号或密码错误")
        # 3. 生成 JWT 并写入 Redis 会话
        token, expire_at = create_access_token(user.id, user.user_name, self.settings)
        session_payload = {
            "id": user.id,
            "userCode": user.user_code,
            "userName": user.user_name,
            "userSex": user.user_sex,
            "userPhone": user.user_phone,
            "address": user.address,
            "token": token,
            "loginTime": int(datetime.now(UTC).timestamp() * 1000),
        }
        ttl_seconds = self.settings.jwt_expire_minutes * 60
        # 4. 使用用户自定义的最大登录数
        await self.store.save_session(session_payload, ttl_seconds, user.max_login_num)
        return token

    async def logout(self, user_id: int, token: str) -> None:
        """
        1. 删除 Redis 中的会话与索引。
        """
        await self.store.remove_session(str(user_id), token)

    async def get_user(self, user_id: int) -> User | None:
        """
        1. 按主键获取用户。
        """
        query = await self.db.execute(select(User).where(User.id == user_id))
        return query.scalar_one_or_none()
