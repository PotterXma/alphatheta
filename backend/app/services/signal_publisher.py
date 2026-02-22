"""
Redis 信号发布服务

Scanner Daemon → Redis pub/sub → WebSocket Feed → Frontend

Channel: alphatheta:signals
格式: JSON
  {
    "type": "signal",
    "ticker": "AAPL",
    "price": 180.25,
    "rsi": 28.5,
    "ivr": 22.0,
    "direction": "bullish",
    "strategy": "leaps_deep_itm_call",
    "leaps_expiration": "2027-01-15",
    "leaps_dte": 360,
    "call_strike": 145.0,
    "call_ask": 42.50,
    "ts": "2026-02-21T14:30:00Z"
  }
"""

import json
import logging
from datetime import UTC, datetime

logger = logging.getLogger("alphatheta.scanner.redis")

SIGNAL_CHANNEL = "alphatheta:signals"
HEARTBEAT_KEY = "scanner:heartbeat"
HEARTBEAT_TTL = 120  # 2 分钟无心跳 → 告警


async def publish_signal(redis_client, signal_dict: dict) -> bool:
    """
    通过 Redis pub/sub 发布扫描信号

    Returns: True if published successfully
    """
    try:
        payload = {
            "type": "signal",
            **signal_dict,
            "ts": datetime.now(UTC).isoformat(),
        }
        await redis_client.publish(SIGNAL_CHANNEL, json.dumps(payload))
        logger.info(f"📡 Signal published: {signal_dict.get('ticker')} via Redis pub/sub")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to publish signal: {e}")
        return False


async def publish_heartbeat(redis_client, watchlist_count: int, redis_ok: bool) -> bool:
    """
    写入 Scanner 心跳到 Redis (带 TTL)

    监控系统可通过检查此 key 是否存在判断 scanner 是否存活
    """
    try:
        heartbeat = {
            "alive": True,
            "watchlist_count": watchlist_count,
            "redis_ok": redis_ok,
            "ts": datetime.now(UTC).isoformat(),
        }
        await redis_client.set(
            HEARTBEAT_KEY,
            json.dumps(heartbeat),
            ex=HEARTBEAT_TTL,
        )
        logger.debug(f"💓 Heartbeat written (TTL={HEARTBEAT_TTL}s)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to write heartbeat: {e}")
        return False
