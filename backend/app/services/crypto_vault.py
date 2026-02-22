"""
凭证加密金库 — Fernet 对称加密

⚠️ 安全约束:
- FERNET_KEY 必须通过环境变量注入, 绝不可硬编码
- 若 FERNET_KEY 缺失, 加密/解密操作抛异常 (fail-fast)
- 密文格式: Fernet base64 token, 内含 HMAC-SHA256 认证

用法:
    from app.services.crypto_vault import encrypt_secret, decrypt_secret
    ciphertext = encrypt_secret("my-broker-api-secret")
    plaintext = decrypt_secret(ciphertext)
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

logger = logging.getLogger("alphatheta.crypto")

# 延迟初始化的 Fernet 实例
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """获取 Fernet 实例 (延迟初始化)"""
    global _fernet
    if _fernet is None:
        settings = get_settings()
        key = settings.fernet_key
        if not key:
            raise RuntimeError(
                "FERNET_KEY 环境变量未设置! "
                "请运行 python3 -c 'from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())' 生成密钥"
            )
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """
    加密敏感数据 (如 API Secret)

    Returns: Fernet base64 密文字符串
    """
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """
    解密敏感数据

    Returns: 原始明文字符串
    Raises: cryptography.fernet.InvalidToken 如果密文被篡改或密钥不匹配
    """
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("❌ Fernet 解密失败 — 密钥不匹配或密文被篡改")
        raise
