#!/usr/bin/env python3
"""
加密算法迁移脚本

用于将旧的 SHA-256 加密的 API Key 迁移到新的 PBKDF2 加密。

使用方法:
    cd backend
    uv run python scripts/migrate_crypto.py

注意：
1. 运行前请备份数据库
2. 确保 .env 文件配置正确
3. 迁移过程中会暂时解密 API Key，请在安全环境中运行
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.core.db import get_async_session_maker
from app.core.settings import get_settings
from app.utils.crypto_migration import migrate_encrypted_api_keys, verify_migration


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("API Key 加密算法迁移工具")
    logger.info("=" * 60)

    settings = get_settings()

    # 警告信息
    logger.warning("⚠️  重要提示:")
    logger.warning("1. 此操作会修改数据库中的加密数据")
    logger.warning("2. 请确保已备份数据库")
    logger.warning("3. 迁移过程中请勿中断")
    logger.warning("")

    # 确认操作
    response = input("是否继续？(yes/no): ")
    if response.lower() != "yes":
        logger.info("操作已取消")
        return

    # 创建数据库会话
    async_session_maker = get_async_session_maker(settings)

    async with async_session_maker() as db:
        # 执行迁移
        logger.info("\n开始迁移...")
        stats = await migrate_encrypted_api_keys(db)

        # 显示结果
        logger.info("\n" + "=" * 60)
        logger.info("迁移结果:")
        logger.info(f"  ✓ 成功: {stats['success']}")
        logger.info(f"  ✗ 失败: {stats['failed']}")
        logger.info(f"  ⊘ 跳过: {stats['skipped']}")
        logger.info("=" * 60)

        # 验证迁移
        if stats["success"] > 0:
            logger.info("\n开始验证迁移结果...")
            all_success = await verify_migration(db)

            if all_success:
                logger.info("\n✅ 所有 API Key 验证成功！迁移完成。")
            else:
                logger.error("\n❌ 部分 API Key 验证失败，请检查日志。")
                sys.exit(1)
        else:
            logger.info("\n没有需要迁移的数据。")


if __name__ == "__main__":
    asyncio.run(main())
