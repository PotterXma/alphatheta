"""
认证路由 — 注册 / 登录 / 令牌刷新
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import AccountType, User
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger("alphatheta.auth")
router = APIRouter()


# ── Request / Response Schemas ──

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ──

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册 — 创建账户并返回 JWT"""

    # 检查 email 是否已注册
    existing = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # 检查 username 是否已存在
    existing_name = await db.execute(
        select(User).where(User.username == body.username)
    )
    if existing_name.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    # 创建用户
    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        account_type=AccountType.PAPER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"✅ New user registered: {user.username} ({user.email})")

    return TokenResponse(
        access_token=create_access_token(user.user_id, user.account_type.value),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录 — 校验凭证并返回 JWT"""

    result = await db.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    # 通用错误消息防止 email 枚举
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )

    logger.info(f"✅ User logged in: {user.username}")

    return TokenResponse(
        access_token=create_access_token(user.user_id, user.account_type.value),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """令牌刷新 — 用 Refresh Token 换取新的 Access + Refresh Token"""

    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token",
        )

    # 验证用户仍然存在且激活
    import uuid
    user_id = uuid.UUID(payload["sub"])
    user = await db.get(User, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    return TokenResponse(
        access_token=create_access_token(user.user_id, user.account_type.value),
        refresh_token=create_refresh_token(user.user_id),
    )
