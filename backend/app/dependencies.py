"""
AlphaTheta Backend — 依赖注入 (DI) 容器
提供 DB Session、Redis Client、Broker Adapter 的 FastAPI Depends
"""

from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import EnvMode, get_settings

# ── 数据库引擎 (延迟初始化) ──
_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends: 异步数据库会话"""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Redis 客户端 ──
_redis_client = None


async def get_redis() -> aioredis.Redis:
    """FastAPI Depends: Redis 异步客户端"""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


# ── Broker Adapter 工厂 ──
def get_broker_adapter():
    """FastAPI Depends: 根据 ENV_MODE 返回对应的 Broker Adapter"""
    from app.adapters.broker_base import BrokerAdapter

    settings = get_settings()

    if settings.env_mode == EnvMode.PAPER:
        from app.adapters.paper import PaperBrokerAdapter

        return PaperBrokerAdapter()
    else:
        if settings.broker_provider == "tradier":
            from app.adapters.tradier import TradierAdapter

            return TradierAdapter(
                api_key=settings.broker_api_key,
                base_url=settings.broker_base_url,
            )
        else:
            raise ValueError(f"Unknown broker provider: {settings.broker_provider}")


# ── 认证依赖 ──

from fastapi import Depends, HTTPException, Request


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI Depends: 获取当前认证用户

    前置条件: AuthMiddleware 已将 user_id 注入 request.state
    返回: User ORM 实例
    抛出: 401 如果未认证或用户不存在

    用法:
        from app.dependencies import get_current_user
        @router.get("/my-data")
        async def my_endpoint(user = Depends(get_current_user)):
            ...
    """
    from app.models.user import User

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
