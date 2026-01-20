"""
API Key 加密工具

使用 Fernet 对称加密保护用户 API Key。
密钥从 jwt_secret 通过 PBKDF2 派生，提供更强的安全性。
"""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.settings import get_settings

# 固定盐值（用于密钥派生）
# 注意：在生产环境中，建议将盐值存储在环境变量中
_SALT = b"my-agent-api-key-encryption-salt-v1"


def _derive_key(secret: str) -> bytes:
    """
    从 jwt_secret 派生 Fernet 密钥（使用 PBKDF2）

    使用 PBKDF2 密钥派生函数，相比 SHA-256 提供更强的安全性：
    - 使用固定盐值防止彩虹表攻击
    - 100,000 次迭代增加破解难度
    - 符合 NIST 安全标准

    Args:
        secret: JWT 密钥字符串

    Returns:
        32 字节的 base64 编码密钥
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # Fernet 需要 32 字节密钥
        salt=_SALT,
        iterations=100000,  # NIST 推荐至少 10,000 次，使用 100,000 次提高安全性
    )
    key_bytes = kdf.derive(secret.encode())
    # Fernet 要求 base64 编码的 32 字节密钥
    return base64.urlsafe_b64encode(key_bytes)


def get_cipher() -> Fernet:
    """
    获取加密器实例

    Returns:
        Fernet 加密器
    """
    settings = get_settings()
    key = _derive_key(settings.jwt_secret)
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """
    加密 API Key

    Args:
        api_key: 明文 API Key

    Returns:
        加密后的字符串（base64 编码）
    """
    cipher = get_cipher()
    encrypted = cipher.encrypt(api_key.encode())
    return encrypted.decode()


def decrypt_api_key(encrypted: str) -> str:
    """
    解密 API Key

    Args:
        encrypted: 加密后的 API Key 字符串

    Returns:
        明文 API Key
    """
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted.encode())
    return decrypted.decode()
