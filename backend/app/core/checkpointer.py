"""
LangGraph Checkpointer - PostgreSQL 实现

使用 AsyncPostgresSaver 将对话状态持久化到 PostgreSQL。
使用连接池避免每次请求都创建新连接。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from loguru import logger
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.settings import Settings

# 全局连接池
_pool: AsyncConnectionPool | None = None
_tables_initialized = False


async def check_connection(conn: AsyncConnection) -> None:
    """
    连接健康检查回调函数。
    在从连接池获取连接时调用，验证连接是否仍然有效。
    如果连接无效，抛出异常，连接池会自动丢弃该连接并获取新连接。
    """
    await conn.execute("SELECT 1")


def get_postgres_url(settings: Settings) -> str:
    """构建 PostgreSQL 连接 URL（psycopg 格式）"""
    return (
        f"postgresql://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


async def init_checkpointer_pool(settings: Settings) -> None:
    """初始化全局连接池（应用启动时调用）"""
    global _pool, _tables_initialized
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=get_postgres_url(settings),
            min_size=5,  # 增加最小连接数，减少连接创建延迟
            max_size=20,  # 增加最大连接数，支持更高并发
            max_idle=300,  # 空闲连接最多保持 5 分钟
            timeout=30,  # 添加连接获取超时（30秒），避免无限等待
            check=check_connection,  # 获取连接前验证有效性
            open=False,
        )
        logger.info(
            "Checkpointer pool created: min_size=5, max_size=20, timeout=30s, health_check=enabled"
        )
        await _pool.open()
        # 初始化表结构（需要在 autocommit 模式下执行，因为 CREATE INDEX CONCURRENTLY 不能在事务中运行）
        async with _pool.connection() as conn:
            # 回滚任何可能的事务（健康检查可能隐式开启事务），然后设置 autocommit 模式
            await conn.rollback()
            await conn.set_autocommit(True)
            try:
                checkpointer = AsyncPostgresSaver(conn)
                await checkpointer.setup()
            except Exception:
                # 表可能已存在，忽略错误
                pass
            finally:
                await conn.set_autocommit(False)
        _tables_initialized = True


async def close_checkpointer_pool() -> None:
    """关闭连接池（应用关闭时调用）"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def create_checkpointer(settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
    """
    创建 LangGraph 异步 PostgreSQL checkpointer（复用连接池）
    """
    global _pool, _tables_initialized

    if _pool is None:
        await init_checkpointer_pool(settings)

    async with _pool.connection() as conn:
        yield AsyncPostgresSaver(conn)


# 兼容旧代码
create_redis_checkpointer = create_checkpointer
