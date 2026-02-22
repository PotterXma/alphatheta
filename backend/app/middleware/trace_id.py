"""
AlphaTheta v2 — Trace ID Middleware

每个 HTTP 请求注入 UUID Trace ID:
1. 从 X-Trace-ID header 读取 (允许上游传入)
2. 无则生成新 UUID
3. 绑定到 contextvars (loguru 自动拾取)
4. 响应 header 回传 X-Trace-ID
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging.logger_setup import trace_id_var, logger


class TraceIdMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware — 全链路 Trace ID 注入。

    执行顺序: 最外层 (在 RateLimit 之前)
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 优先使用上游传入的 Trace ID (网关/负载均衡器场景)
        incoming_trace = request.headers.get("X-Trace-ID")
        tid = incoming_trace if incoming_trace else uuid.uuid4().hex[:16]

        # 绑定到 contextvars (loguru patcher 会自动读取)
        token = trace_id_var.set(tid)

        try:
            # 请求到达日志
            logger.info(
                "→ {method} {path}",
                method=request.method,
                path=request.url.path,
            )

            response = await call_next(request)

            # 注入响应 header
            response.headers["X-Trace-ID"] = tid

            # 响应日志
            logger.info(
                "← {status} {method} {path}",
                status=response.status_code,
                method=request.method,
                path=request.url.path,
            )

            return response
        except Exception as exc:
            logger.exception(
                "💥 Unhandled exception in {method} {path}",
                method=request.method,
                path=request.url.path,
            )
            raise
        finally:
            # 恢复 contextvars
            trace_id_var.reset(token)
