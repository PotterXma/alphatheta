"""
访客 IP 追踪中间件 — 基于 Redis 的轻量级统计

Redis 数据结构:
- alphatheta:visitors:ips        → ZSET (member=IP, score=last_seen_ts)
- alphatheta:visitors:daily:{date} → HyperLogLog (每日独立 UV)
- alphatheta:visitors:hits       → STRING (总请求计数器)
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("alphatheta.visitors")

# 排除的路径 (健康检查、静态资源等)
_SKIP_PATHS = frozenset({"/healthz", "/readyz", "/metrics", "/favicon.ico"})
_SKIP_PREFIXES = ("/js/", "/img/", "/fonts/")


class VisitorTrackingMiddleware(BaseHTTPMiddleware):
    """
    轻量级访客追踪 — 每个请求记录 IP 到 Redis

    开销极低: 3 个 pipeline 命令, ~0.1ms
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 跳过内部探针和静态资源
        path = request.url.path
        if path in _SKIP_PATHS or path.startswith(_SKIP_PREFIXES):
            return response

        try:
            from app.dependencies import get_redis
            redis = await get_redis()

            # 提取真实 IP (支持反向代理)
            ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or request.headers.get("X-Real-IP", "")
                or request.client.host
            )

            now = time.time()
            today = time.strftime("%Y-%m-%d")

            pipe = redis.pipeline(transaction=False)
            # 1. IP 加入有序集合 (score=最后访问时间)
            pipe.zadd("alphatheta:visitors:ips", {ip: now})
            # 2. 每日 HyperLogLog UV
            pipe.pfadd(f"alphatheta:visitors:daily:{today}", ip)
            # 3. 总请求计数 +1
            pipe.incr("alphatheta:visitors:hits")
            # 4. 记录该 IP 的请求路径 (最近的)
            pipe.hincrby(f"alphatheta:visitors:paths", path, 1)
            await pipe.execute()

        except Exception:
            # 统计失败绝不影响正常请求
            pass

        return response
