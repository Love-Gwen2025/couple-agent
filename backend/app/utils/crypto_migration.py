"""
加密算法迁移工具

用于将旧的 SHA-256 加密数据迁移到新的 PBKDF2 加密。
仅在升级时使用一次。
"""

import base64
import hashlib

from cryptography.fernet import Fernet
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.models.user_model import UserModel


def _derive_key_old(secret: str) -> bytes:
    """
    旧的密钥派生方法（SHA-256）

    仅用于迁移，解密旧数据
    """
    key_bytes = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


def _get_old_cipher() -> Fernet:
    """获取旧的加密器（用于解密旧数据）"""
    settings = get_settings()
    key = _derive_key_old(settings.jwt_secret)
    return Fernet(key)


async def migrate_encrypted_api_keys(db: AsyncSession) -> dict[str, int]:
    """
    迁移所有用户模型的加密 API Key

    从旧的 SHA-256 加密迁移到新的 PBKDF2 加密

    Args:
        db: 数据库会话

    Returns:
        迁移统计信息 {"success": 成功数, "failed": 失败数, "skipped": 跳过数}
    """
    from app.core.crypto import encrypt_api_key

    stats = {"success": 0, "failed": 0, "skipped": 0}

    # 获取所有用户模型
    result = await db.execute(select(UserModel))
    user_models = result.scalars().all()

    logger.info(f"开始迁移 {len(user_models)} 个用户模型的 API Key 加密...")

    old_cipher = _get_old_cipher()

    for model in user_models:
        try:
            # 尝试用旧算法解密
            try:
                decrypted = old_cipher.decrypt(model.api_key.encode()).decode()
            except Exception:
                # 解密失败，可能已经是新算法加密的，或者数据损坏
                logger.warning(f"模型 {model.id} 的 API Key 无法用旧算法解密，跳过")
                stats["skipped"] += 1
                continue

            # 用新算法重新加密
            new_encrypted = encrypt_api_key(decrypted)

            # 更新数据库
            await db.execute(
                update(UserModel)
                .where(UserModel.id == model.id)
                .values(api_key=new_encrypted)
            )

            stats["success"] += 1
            logger.info(f"成功迁移模型 {model.id} ({model.model_name})")

        except Exception as e:
            logger.error(f"迁移模型 {model.id} 失败: {e}")
            stats["failed"] += 1

    await db.commit()

    logger.info(
        f"迁移完成: 成功 {stats['success']}, 失败 {stats['failed']}, 跳过 {stats['skipped']}"
    )

    return stats


async def verify_migration(db: AsyncSession) -> bool:
    """
    验证迁移是否成功

    尝试用新算法解密所有 API Key

    Args:
        db: 数据库会话

    Returns:
        是否所有 API Key 都能成功解密
    """
    from app.core.crypto import decrypt_api_key

    result = await db.execute(select(UserModel))
    user_models = result.scalars().all()

    all_success = True

    for model in user_models:
        try:
            decrypt_api_key(model.api_key)
            logger.info(f"✓ 模型 {model.id} ({model.model_name}) 验证成功")
        except Exception as e:
            logger.error(f"✗ 模型 {model.id} ({model.model_name}) 验证失败: {e}")
            all_success = False

    return all_success
