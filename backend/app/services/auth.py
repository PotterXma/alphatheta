"""
认证服务 — JWT 令牌生成 + 密码哈希

设计:
- Access Token: 15 分钟有效期, 携带 user_id + account_type
- Refresh Token: 7 天有效期, 仅携带 user_id
- 密码: bcrypt 哈希, 自动 salt
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.config import get_settings

# ── 密码哈希上下文 ──
# bcrypt >= 4.1 严格限制 72 字节, 需要 truncate_error=False 忽略
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False,
)


def hash_password(password: str) -> str:
    """明文密码 → bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码是否匹配哈希"""
    return pwd_context.verify(plain, hashed)


def create_access_token(
    user_id: uuid.UUID,
    account_type: str = "paper",
    expires_minutes: int = 15,
) -> str:
    """生成 JWT Access Token (短期)"""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "acct": account_type,
        "exp": datetime.now(UTC) + timedelta(minutes=expires_minutes),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def create_refresh_token(
    user_id: uuid.UUID,
    expires_days: int = 7,
) -> str:
    """生成 JWT Refresh Token (长期)"""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=expires_days),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    """
    解码 JWT Token

    Returns:
        dict with keys: sub (user_id str), type (access/refresh), acct, exp, iat

    Raises:
        jwt.ExpiredSignatureError: 令牌过期
        jwt.InvalidTokenError: 令牌无效
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
