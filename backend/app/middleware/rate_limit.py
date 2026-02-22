"""速率限制中间件 — 100 req/min per IP"""

import time
import logging
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("alphatheta.middleware.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    WINDOW_SECONDS = 60
    MAX_REQUESTS = 100

    def __init__(self, app):
        super().__init__(app)
        self._access_log: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.WINDOW_SECONDS

        # 清理过期记录
        self._access_log[client_ip] = [
            t for t in self._access_log[client_ip] if t > cutoff
        ]

        if len(self._access_log[client_ip]) >= self.MAX_REQUESTS:
            return Response(
                content='{"error": "Rate limit exceeded (100/min)"}',
                status_code=429,
                media_type="application/json",
            )

        self._access_log[client_ip].append(now)
        return await call_next(request)
