"""
数据库初始化模块

在应用启动时自动执行 SQL 迁移脚本，确保数据库表结构是最新的。
所有语句使用 IF NOT EXISTS，可重复执行。
"""

from pathlib import Path

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.settings import Settings


async def init_database(settings: Settings) -> None:
    """
    执行数据库初始化脚本

    在应用启动时调用，自动创建所有表结构。
    由于使用 IF NOT EXISTS，重复执行不会有副作用。

    Args:
        settings: 应用配置
    """
    # 查找迁移脚本
    # 优先从 /app/migrations 读取（Docker 环境）
    # 其次从相对路径读取（本地开发环境）
    migration_paths = [
        Path("/app/migrations/init_schema.sql"),  # Docker 环境
        Path(__file__).parent.parent.parent / "migrations" / "init_schema.sql",  # 本地开发
    ]

    sql_file = None
    for path in migration_paths:
        if path.exists():
            sql_file = path
            break

    if sql_file is None:
        logger.warning("⚠️ 未找到数据库迁移脚本 init_schema.sql，跳过自动迁移")
        return

    logger.info(f"📦 开始执行数据库迁移: {sql_file}")

    try:
        # 读取 SQL 脚本内容
        sql_content = sql_file.read_text(encoding="utf-8")

        # 创建临时引擎执行迁移
        engine = create_async_engine(
            settings.database_url,
            echo=False,
        )

        async with engine.begin() as conn:
            # 执行整个脚本
            # 分割语句并逐条执行（处理多语句脚本）
            statements = [s.strip() for s in sql_content.split(";") if s.strip()]
            for stmt in statements:
                # 跳过注释和空行
                if stmt.startswith("--") or not stmt:
                    continue
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    # 记录错误但继续执行（某些语句可能因已存在而失败）
                    logger.debug(f"SQL 语句执行跳过: {str(e)[:100]}")

        await engine.dispose()
        logger.info("✅ 数据库迁移完成")

    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        # 不抛出异常，允许应用继续启动（表可能已存在）
