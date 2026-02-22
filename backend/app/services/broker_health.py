"""
券商健康监控 — 维护时段静默 + 网关健康检查

核心问题:
  券商 (如 Tradier, IBKR) 每天有固定维护时段:
  - Tradier: 17:00-17:30 ET
  - IBKR: 23:45-00:45 ET (网关重启)
  
  如果在维护时段发送请求, 会收到 503/Connection Reset,
  如果不处理, 会触发报错风暴 + 重试风暴, 淹没日志。

解决方案:
  1. @require_broker_healthy 装饰器: 自动检测维护时段, 安静挂起
  2. BrokerHealthMonitor: 轮询 /watchlists (轻量 GET) 检查网关状态
  3. 维护时段内所有请求返回 "maintenance" 而不是报错
"""

import asyncio
import functools
import logging
from datetime import datetime, timezone

logger = logging.getLogger("alphatheta.broker_health")


class BrokerHealthMonitor:
    """
    券商健康监控器

    机制:
    1. 维护已知的维护时段窗口
    2. 定期 ping 券商 API (低频, 每 60 秒)
    3. 提供 is_healthy 属性给所有调用方检查
    """

    # 已知维护时段 (UTC 时间, hour:minute)
    # Tradier: 17:00-17:30 ET → 22:00-22:30 UTC (冬令时)
    MAINTENANCE_WINDOWS = [
        {"start": (22, 0), "end": (22, 30), "broker": "Tradier"},
        {"start": (4, 45), "end": (5, 45), "broker": "IBKR"},  # 23:45-00:45 ET
    ]

    def __init__(self):
        self._is_healthy = True
        self._last_check: datetime | None = None
        self._consecutive_failures = 0
        self._max_failures_before_alarm = 3

    @property
    def is_healthy(self) -> bool:
        """
        券商是否健康 — 综合判断:
        1. 不在已知维护时段
        2. 最近一次 ping 成功
        """
        if self._is_in_maintenance_window():
            return False
        return self._is_healthy

    def _is_in_maintenance_window(self) -> bool:
        """检查当前时间是否在已知维护时段内"""
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        current_minute = now.minute

        for window in self.MAINTENANCE_WINDOWS:
            start_h, start_m = window["start"]
            end_h, end_m = window["end"]

            # 简单区间检查 (不跨日)
            start_total = start_h * 60 + start_m
            end_total = end_h * 60 + end_m
            current_total = current_hour * 60 + current_minute

            if start_total <= current_total <= end_total:
                logger.debug(
                    f"[BrokerHealth] In maintenance window: {window['broker']} "
                    f"({start_h}:{start_m:02d}-{end_h}:{end_m:02d} UTC)"
                )
                return True

        return False

    async def ping(self, broker_adapter=None) -> bool:
        """
        轻量 ping — 调用 /watchlists 或 /clock 检查券商可达性

        成功: 重置失败计数
        失败: 累计失败, 超过阈值报警
        """
        try:
            if broker_adapter and hasattr(broker_adapter, "_request"):
                # 使用最轻量的 GET 请求
                await broker_adapter._request("GET", "/markets/clock")
            self._is_healthy = True
            self._consecutive_failures = 0
            self._last_check = datetime.now(timezone.utc)
            return True

        except Exception as e:
            self._consecutive_failures += 1
            self._last_check = datetime.now(timezone.utc)

            if self._consecutive_failures >= self._max_failures_before_alarm:
                self._is_healthy = False
                logger.error(
                    f"[BrokerHealth] {self._consecutive_failures} consecutive failures: {e}"
                )
            else:
                logger.warning(f"[BrokerHealth] Ping failed ({self._consecutive_failures}x): {e}")

            return False

    def get_status(self) -> dict:
        """获取健康状态 — 供前端展示"""
        return {
            "is_healthy": self.is_healthy,
            "in_maintenance": self._is_in_maintenance_window(),
            "consecutive_failures": self._consecutive_failures,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }


# ── 模块级单例 ──
_health_monitor = BrokerHealthMonitor()


def get_health_monitor() -> BrokerHealthMonitor:
    return _health_monitor


def require_broker_healthy(func):
    """
    装饰器: 要求券商健康才执行

    在维护时段或券商不可达时:
    - 不执行任何交易操作
    - 返回 { "status": "maintenance", "reason": "..." }
    - 不报错, 不重试, 安静等待

    使用:
        @require_broker_healthy
        async def submit_order(...):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        monitor = get_health_monitor()

        if not monitor.is_healthy:
            status = monitor.get_status()
            reason = "券商维护时段" if status["in_maintenance"] else "券商网关不可达"
            logger.info(f"[BrokerHealth] Skipping {func.__name__}: {reason}")
            return {
                "status": "maintenance",
                "reason": reason,
                "details": status,
            }

        return await func(*args, **kwargs)

    return wrapper
