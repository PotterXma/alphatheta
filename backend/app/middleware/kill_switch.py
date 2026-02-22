"""
全局熔断中间件 — 交易系统最后一道防线

设计要点:
1. 拦截所有非 GET/HEAD/OPTIONS 请求（即所有突变操作）
2. 环境感知: 从 config 或请求 Header X-Env-Mode 获取当前环境 (paper/live)
3. Redis Key 检查: system:kill_switch:{env}
4. 熔断激活时返回 503 Service Unavailable（非 403，因为这不是权限问题而是系统状态）
5. 内存缓存 + 短 TTL 避免每次请求都打 Redis

并发控制:
- Redis 读取是幂等的，无并发风险
- 本地缓存 1 秒钟减少 Redis 压力，可接受 1s 的熔断延迟
"""

import json
import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.dependencies import get_redis

logger = logging.getLogger("alphatheta.middleware.kill_switch")

# 本地缓存: 避免每个请求都查 Redis
_cache: dict[str, tuple[bool, str | None, float]] = {}  # env → (active, reason, timestamp)
_CACHE_TTL: float = 1.0  # 1 秒本地缓存，平衡实时性与性能

# 安全放行的 HTTP 方法 — 读操作不受熔断影响
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# 不受熔断影响的路径前缀 (管理端点需要始终可用以关闭熔断)
_EXEMPT_PATHS = frozenset({
    "/healthz", "/readyz", "/metrics", "/docs", "/redoc", "/openapi.json",
    "/api/v1/admin/kill-switch",  # 管理员必须能操作熔断开关本身
})


class KillSwitchMiddleware(BaseHTTPMiddleware):
    """
    全局熔断: 检查 Redis 中 system:kill_switch:{env} 的状态

    当熔断激活时:
    - 所有突变操作 (POST/PUT/DELETE/PATCH) 被阻止
    - 返回 503 + 熔断原因
    - 读操作 (GET) 和管理端点不受影响
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # ── 读操作直接放行 ──
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        # ── 豁免路径放行 (管理端点) ──
        path = request.url.path
        for exempt in _EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        # ── 确定环境 ──
        # 优先从 Header 获取，回退到 config
        env = (
            request.headers.get("X-Env-Mode")
            or get_settings().env_mode.value
        )

        # ── 检查熔断状态 (带本地缓存) ──
        is_active, reason = await self._check_kill_switch(env)

        if is_active:
            logger.warning(
                f"🔴 KILL SWITCH BLOCKED: {request.method} {path} "
                f"[env={env}] reason={reason}"
            )
            return Response(
                content=json.dumps({
                    "error": "System halted — kill switch active",
                    "reason": reason or "No reason provided",
                    "env_mode": env,
                    "hint": "Contact admin to deactivate kill switch via POST /api/v1/admin/kill-switch",
                }),
                status_code=503,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        return await call_next(request)

    async def _check_kill_switch(self, env: str) -> tuple[bool, str | None]:
        """
        检查熔断状态 — 带 1 秒本地缓存

        设计: 本地缓存避免每个请求都查 Redis。
        最坏情况: 熔断激活后最多 1 秒延迟生效。
        对交易系统来说 1 秒延迟完全可接受。
        """
        now = time.monotonic()

        # 检查本地缓存
        if env in _cache:
            active, reason, ts = _cache[env]
            if now - ts < _CACHE_TTL:
                return active, reason

        # 查 Redis
        try:
            redis = await get_redis()
            redis_key = f"system:kill_switch:{env}"
            value = await redis.get(redis_key)

            # value 格式: "1" (active) 或 "0"/None (inactive)
            # 扩展格式: "1:Manual halt for maintenance" (带原因)
            if value and value.startswith("1"):
                reason = value.split(":", 1)[1] if ":" in value else None
                _cache[env] = (True, reason, now)
                return True, reason
            else:
                _cache[env] = (False, None, now)
                return False, None

        except Exception as e:
            # Redis 不可用时的安全策略:
            # 保守选择: 熔断放行（安全失败）
            # 激进选择: 熔断阻止（安全拒绝）
            # 这里选择放行 — 因为 Redis 挂了但 PG 中有数据，恢复后会同步
            logger.error(f"Kill switch check failed (safe-pass): {e}")
            return False, None
