"""
AlphaTheta Scanner — 美股交易时间日历

提供:
  - isUSMarketOpen(): 判断当前是否在美东工作日 09:30-16:00
  - get_sleep_seconds(): 闭市时计算距下一次检查应休眠的秒数
  - is_heartbeat_time(): 判断是否到达 09:20 心跳窗口
"""

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger("alphatheta.scanner.calendar")

ET = ZoneInfo("America/New_York")

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
HEARTBEAT_TIME = time(9, 20)
HEARTBEAT_WINDOW_MINUTES = 2  # 09:20 ~ 09:22 窗口内只触发一次


def now_et() -> datetime:
    """当前美东时间"""
    return datetime.now(ET)


def isUSMarketOpen() -> bool:
    """
    判断当前是否在美股常规交易时段 (美东工作日 09:30-16:00)

    自动处理 EST/EDT (DST) 切换 — zoneinfo 保证。
    """
    dt = now_et()

    # 周末: Mon=0 .. Sun=6
    if dt.weekday() >= 5:
        return False

    current_time = dt.time()
    return MARKET_OPEN <= current_time < MARKET_CLOSE


def get_sleep_seconds(scan_interval: int = 900) -> int:
    """
    计算应休眠的秒数

    - 交易时段: 返回 scan_interval (默认 15 分钟)
    - 闭市: 返回距下一个交易日 09:15 的秒数 (提前 15 分钟唤醒做心跳)
    """
    dt = now_et()
    current_time = dt.time()

    # 交易时段中 → 正常间隔
    if dt.weekday() < 5 and MARKET_OPEN <= current_time < MARKET_CLOSE:
        return scan_interval

    # 计算下一个交易日的 09:15
    next_day = dt + timedelta(days=1)
    while next_day.weekday() >= 5:  # 跳过周末
        next_day += timedelta(days=1)

    next_wake = next_day.replace(
        hour=9, minute=15, second=0, microsecond=0, tzinfo=ET
    )

    # 如果当前是工作日盘前 (< 09:15), 今天就唤醒
    if dt.weekday() < 5 and current_time < time(9, 15):
        next_wake = dt.replace(
            hour=9, minute=15, second=0, microsecond=0
        )

    sleep_secs = max(60, int((next_wake - dt).total_seconds()))
    logger.info(f"💤 闭市休眠 {sleep_secs}s (下次唤醒: {next_wake.strftime('%Y-%m-%d %H:%M ET')})")
    return sleep_secs


def is_heartbeat_time() -> bool:
    """判断是否在 09:20-09:22 ET 心跳窗口内"""
    dt = now_et()
    if dt.weekday() >= 5:
        return False
    current_time = dt.time()
    end = time(HEARTBEAT_TIME.hour, HEARTBEAT_TIME.minute + HEARTBEAT_WINDOW_MINUTES)
    return HEARTBEAT_TIME <= current_time < end
