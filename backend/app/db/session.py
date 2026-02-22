"""
异步数据库会话工厂

后台任务没有 FastAPI 的 Request 上下文,
必须通过此工厂手动创建和管理数据库会话。

用法:
    async with get_async_session() as session:
        result = await session.execute(select(Order))
        await session.commit()
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

# ── 模块级单例 (延迟初始化) ──
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    """获取引擎单例 — 延迟初始化, 避免 import-time 读取 settings"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=5,           # 后台任务池不用太大
            max_overflow=2,
            pool_pre_ping=True,    # 自动检测死连接
            pool_recycle=1800,     # 30 分钟回收连接
        )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取 session 工厂单例"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,   # 防止 commit 后字段访问触发 lazy load
        )
    return _session_factory


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    后台任务专用的 DB 会话上下文管理器

    自动处理 commit/rollback/close:
    - 正常退出 → commit
    - 异常退出 → rollback
    - 始终关闭连接

    用法:
        async with get_async_session() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.FILLED
            # 退出时自动 commit
    """
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_engine() -> None:
    """关闭引擎连接池 — 在 app shutdown 时调用"""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
