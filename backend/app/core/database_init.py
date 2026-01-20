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
            # 逐条执行 SQL 语句
            # 使用更可靠的方式分割：按换行+分号分割，保留完整语句
            statements = _parse_sql_statements(sql_content)

            executed_count = 0
            for stmt in statements:
                try:
                    await conn.execute(text(stmt))
                    executed_count += 1
                except Exception as e:
                    # 记录失败的语句（可能是已存在等原因）
                    error_msg = str(e)[:200]
                    # 只记录非预期错误，跳过"已存在"类型的错误
                    if (
                        "already exists" not in error_msg.lower()
                        and "duplicate" not in error_msg.lower()
                    ):
                        logger.warning(f"SQL 语句执行警告: {error_msg}")

            logger.info(f"✅ 数据库迁移完成，成功执行 {executed_count} 条语句")

        await engine.dispose()

    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        # 不抛出异常，允许应用继续启动（表可能已存在）


def _parse_sql_statements(sql_content: str) -> list[str]:
    """
    解析 SQL 脚本，提取可执行的语句

    处理多行语句、注释等情况
    """
    statements = []
    current_stmt = []

    for line in sql_content.split("\n"):
        # 去除首尾空白
        stripped = line.strip()

        # 跳过空行和纯注释行
        if not stripped or stripped.startswith("--"):
            continue

        # 移除行尾注释（保留行内内容）
        if "--" in stripped:
            # 简单处理：只保留 -- 之前的内容
            # 注意：这不处理字符串内的 -- ，但对于 DDL 语句足够了
            stripped = stripped.split("--")[0].strip()
            if not stripped:
                continue

        current_stmt.append(stripped)

        # 检查语句是否结束（以分号结尾）
        if stripped.endswith(";"):
            stmt = " ".join(current_stmt)
            # 移除末尾分号
            stmt = stmt.rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current_stmt = []

    # 处理最后一条没有分号的语句
    if current_stmt:
        stmt = " ".join(current_stmt).rstrip(";").strip()
        if stmt:
            statements.append(stmt)

    return statements
