from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import Settings, get_settings


def build_database_url(cfg: Settings) -> str:
    """
    1. 拼接 PostgreSQL 连接串，复用 asyncpg 驱动支持 async 会话。
    """
    return (
        f"postgresql+asyncpg://{cfg.db_user}:{cfg.db_password}"
        f"@{cfg.db_host}:{cfg.db_port}/{cfg.db_name}"
    )


def create_engine(cfg: Settings) -> AsyncEngine:
    """
    1. 创建异步引擎并限制池大小，适配 1C2G 部署环境。
    """
    return create_async_engine(
        build_database_url(cfg),
        pool_size=cfg.db_pool_size,
        max_overflow=cfg.db_max_overflow,
        echo=False,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    1. 创建 Session 工厂，关闭自动过期以便业务层灵活控制。
    """
    return async_sessionmaker(engine, expire_on_commit=False)


settings = get_settings()
engine = create_engine(settings)
SessionLocal = create_session_factory(engine)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    1. FastAPI 依赖项：按请求获取异步 Session，并在请求结束时关闭。
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close()
