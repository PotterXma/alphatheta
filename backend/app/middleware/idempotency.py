"""
幂等性中间件 — 防止网络重试导致的重复下单

设计要点:
1. 仅对 POST 请求且携带 Idempotency-Key Header 的请求生效
2. Redis SETNX 原子操作保证并发安全：同一 Key 只有一个请求能"抢占"执行权
3. 执行成功后，将完整 HTTP 响应（status + body）异步写入 Redis，TTL 24h
4. 后续重复请求直接返回缓存，并附带 X-Idempotent-Replay: true Header
5. Key 格式: idempotency:{env}:{uuid}，环境隔离

并发控制:
- SETNX + TTL 组合防止死锁：即使请求崩溃，Key 也会在 300s 后自动释放
- 两阶段写入: 先写 "processing" 占位 → 请求完成后覆写实际结果
"""

import json
import logging
import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.dependencies import get_redis

logger = logging.getLogger("alphatheta.middleware.idempotency")

# 幂等结果缓存 TTL: 24 小时
RESULT_TTL: int = 86400
# 处理中占位 TTL: 5 分钟（防止崩溃后死锁）
PROCESSING_TTL: int = 300

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 中间件: 基于 Idempotency-Key Header 的请求去重

    工作流:
    1. 非 POST 请求 → 直接放行
    2. 无 Idempotency-Key → 对 /submit 端点返回 400，其余放行
    3. Key 格式校验 (UUID v4)
    4. Redis SETNX 抢占 → 成功则执行请求 → 失败则返回缓存或 409 冲突
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # ── 仅拦截 POST 请求 ──
        if request.method != "POST":
            return await call_next(request)

        idem_key: str | None = request.headers.get("Idempotency-Key")
        path: str = request.url.path

        # 对订单提交端点，强制要求 Idempotency-Key
        if not idem_key:
            if "/submit" in path:
                return _json_response(
                    status_code=400,
                    body={"error": "Idempotency-Key header is required for order submission"},
                )
            return await call_next(request)

        # ── UUID 格式校验 ──
        if not _UUID_RE.match(idem_key):
            return _json_response(
                status_code=400,
                body={"error": f"Invalid Idempotency-Key format: must be UUID v4, got '{idem_key}'"},
            )

        settings = get_settings()
        env = settings.env_mode.value
        redis_key = f"idempotency:{env}:{idem_key}"

        try:
            redis = await get_redis()

            # ── 阶段1: SETNX 原子抢占 ──
            # 如果 Key 不存在，写入 "processing" 并设置短 TTL 防止死锁
            acquired = await redis.set(
                redis_key, "processing", nx=True, ex=PROCESSING_TTL
            )

            if not acquired:
                # Key 已存在 → 检查是否有缓存结果
                cached = await redis.get(redis_key)

                if cached == "processing":
                    # 上一个请求还在处理中 → 返回 409 Conflict
                    logger.info(f"Idempotency conflict: key={idem_key} still processing")
                    return _json_response(
                        status_code=409,
                        body={"error": "Request with this Idempotency-Key is still being processed"},
                    )

                # 有缓存结果 → 直接返回
                logger.info(f"Idempotency replay: key={idem_key}")
                try:
                    result = json.loads(cached)
                    return Response(
                        content=result.get("body", ""),
                        status_code=result.get("status_code", 200),
                        media_type="application/json",
                        headers={"X-Idempotent-Replay": "true"},
                    )
                except (json.JSONDecodeError, TypeError):
                    # 缓存损坏 → 删除后放行
                    await redis.delete(redis_key)

            # ── 阶段2: 执行请求 ──
            response = await call_next(request)

            # ── 阶段3: 异步缓存结果 ──
            if 200 <= response.status_code < 300:
                # 读取完整响应体
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()

                # 序列化并写入 Redis，覆盖 "processing" 占位
                cache_value = json.dumps({
                    "status_code": response.status_code,
                    "body": body_bytes.decode("utf-8"),
                })
                await redis.set(redis_key, cache_value, ex=RESULT_TTL)

                # 重建 Response（因为 body_iterator 已被消费）
                return Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            else:
                # 非 2xx → 释放占位，允许重试
                await redis.delete(redis_key)

            return response

        except Exception as e:
            # Redis 不可用时安全降级: 允许请求通过但记录告警
            logger.error(f"Idempotency middleware degraded — Redis error: {e}")
            return await call_next(request)


def _json_response(status_code: int, body: dict) -> Response:
    """快速构建 JSON 响应"""
    return Response(
        content=json.dumps(body),
        status_code=status_code,
        media_type="application/json",
    )
