"""
WebSocket Feed — 频道订阅 + Redis pub/sub 信号转发

v2 升级:
1. 新增 SIGNALS 频道 — 从 Redis alphatheta:signals 自动转发
2. WS 连接支持 JWT 认证 (可选, 通过 ?token= 参数)
3. 后台 Redis subscriber 任务, 生命周期绑定 WS 连接
"""

import asyncio
import json
import logging
import uuid
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("alphatheta.websocket")


class Channel(str, Enum):
    MARKET = "market"
    ORDERS = "orders"
    SIGNALS = "signals"
    SYSTEM_LOGS = "system_logs"


class ConnectionManager:
    """WebSocket 连接管理 + 频道广播"""

    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {c.value: [] for c in Channel}
        self._user_map: dict[WebSocket, uuid.UUID | None] = {}

    async def connect(self, ws: WebSocket, channels: list[str], user_id: uuid.UUID | None = None):
        await ws.accept()
        for ch in channels:
            if ch in self.connections:
                self.connections[ch].append(ws)
        self._user_map[ws] = user_id
        logger.info(f"WS connected, channels={channels}, user={user_id or 'anonymous'}")

    async def disconnect(self, ws: WebSocket):
        for ch_list in self.connections.values():
            if ws in ch_list:
                ch_list.remove(ws)
        self._user_map.pop(ws, None)

    async def broadcast(self, channel: str, data: dict):
        """广播消息到指定频道的所有客户端"""
        message = json.dumps({"channel": channel, "data": data})
        dead = []
        for ws in self.connections.get(channel, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def close_all(self, code: int = 1001):
        """优雅关闭所有连接 (SIGTERM)"""
        for ch_list in self.connections.values():
            for ws in ch_list:
                try:
                    await ws.close(code=code, reason="Server shutting down")
                except Exception:
                    pass
        logger.info("All WebSocket connections closed")


manager = ConnectionManager()

# ── Redis pub/sub → WS 桥接任务 ──
_redis_sub_task: asyncio.Task | None = None


async def _redis_signal_subscriber():
    """
    后台任务: 订阅 Redis alphatheta:signals → 广播到 WS SIGNALS 频道

    生命周期: API 启动时启动, API 关闭时取消
    """
    try:
        from app.dependencies import get_redis
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("alphatheta:signals")
        logger.info("📡 Redis subscriber started: alphatheta:signals → WS")

        async for msg in pubsub.listen():
            if msg["type"] == "message":
                try:
                    data = json.loads(msg["data"])
                    await manager.broadcast("signals", data)
                except Exception as e:
                    logger.warning(f"Signal forward error: {e}")
    except asyncio.CancelledError:
        logger.info("Redis subscriber stopped")
    except Exception as e:
        logger.error(f"Redis subscriber crashed: {e}")


def start_redis_subscriber():
    """启动 Redis 信号订阅器 (在 API startup 中调用)"""
    global _redis_sub_task
    if _redis_sub_task is None or _redis_sub_task.done():
        _redis_sub_task = asyncio.create_task(_redis_signal_subscriber())


def stop_redis_subscriber():
    """停止 Redis 信号订阅器"""
    global _redis_sub_task
    if _redis_sub_task and not _redis_sub_task.done():
        _redis_sub_task.cancel()


def _authenticate_ws(token: str | None) -> uuid.UUID | None:
    """
    WS JWT 认证 (可选)

    有 token → 解码并返回 user_id
    无 token → 返回 None (匿名连接, 仅接收公开信号)
    """
    if not token:
        return None
    try:
        from app.services.auth import decode_token
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except Exception:
        return None


@router.websocket("/ws/feed")
async def websocket_feed(ws: WebSocket):
    """WebSocket 端点 — 支持多频道订阅 + JWT 认证"""
    # JWT 认证 (可选)
    token = ws.query_params.get("token")
    user_id = _authenticate_ws(token)

    # 频道订阅
    channels = ws.query_params.get("channels", "market,orders,signals,system_logs").split(",")

    # 确保 Redis subscriber 在运行
    start_redis_subscriber()

    await manager.connect(ws, channels, user_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        await manager.disconnect(ws)
        logger.info(f"WS client disconnected (user={user_id or 'anonymous'})")
