"""
交易日历中间件 — 美股休市期间阻止所有突变操作

设计要点:
1. 模块加载时初始化 NYSE 日历 (exchange_calendars)，缓存到全局变量
2. 区分读/写: GET/HEAD/OPTIONS 直接放行，POST/PUT/DELETE/PATCH 需检查日历
3. 时区处理: exchange_calendars 返回 UTC 时间，统一在 UTC 下比较
4. 提前闭盘: 利用 calendar.session_close() 自动处理 (如圣诞前夕 13:00 EST)
5. 休市时返回 409 + CalendarStatus JSON，供前端展示倒计时

性能考虑:
- 日历对象在模块加载时创建，运行期间只读
- 每次请求只做一次 pandas Timestamp 比较，性能开销极低 (~0.1ms)
- 节假日列表由 exchange_calendars 维护，无需手动更新
"""

import json
import logging
from datetime import datetime, timezone

import exchange_calendars as xcals
import pandas as pd
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("alphatheta.middleware.calendar")

# ── 模块级初始化: USD/NYSE 交易日历 ──
# exchange_calendars 内置美股所有节假日和提前闭盘日
try:
    _NYSE: xcals.ExchangeCalendar = xcals.get_calendar("XNYS")
    logger.info("NYSE calendar initialized (module-level)")
except Exception as e:
    _NYSE = None
    logger.error(f"Failed to initialize NYSE calendar: {e}")

# 读操作 — 直接放行
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# 豁免路径 — 管理端点和基础设施即使休市也必须可用
_EXEMPT_PATHS = frozenset({
    "/healthz", "/readyz", "/metrics", "/docs", "/redoc", "/openapi.json",
    "/api/v1/admin",  # Kill switch 操作不受日历限制
    "/ws/feed",       # WebSocket 连接不受日历限制
})


class CalendarMiddleware(BaseHTTPMiddleware):
    """
    交易日历守门员

    工作逻辑:
    1. GET 请求 → 放行 (前端随时可查询)
    2. 豁免路径 → 放行
    3. 检查当前 UTC 时间是否在交易时段
    4. 休市 → 409 Conflict + CalendarStatus JSON
    5. 开市 → 放行
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # ── 读操作直接放行 ──
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        # ── 豁免路径放行 ──
        path = request.url.path
        for exempt in _EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)

        # ── 日历未加载 → 安全放行 (降级) ──
        if _NYSE is None:
            logger.warning("Calendar not available — safe-pass")
            return await call_next(request)

        # ── 核心检查: 当前是否在交易时段内 ──
        now_utc = pd.Timestamp.now(tz="UTC")
        is_open, status = _check_market_status(now_utc)

        if not is_open:
            logger.info(
                f"🔒 Calendar BLOCKED: {request.method} {path} — "
                f"market closed, next_open={status.get('next_open', 'unknown')}"
            )
            return Response(
                content=json.dumps({
                    "error": "Market is currently closed",
                    "calendar_status": status,
                }),
                status_code=409,
                media_type="application/json",
            )

        return await call_next(request)


def _check_market_status(now_utc: pd.Timestamp) -> tuple[bool, dict]:
    """
    检查市场状态

    Returns:
        (is_open, calendar_status_dict)

    时区处理说明:
    - exchange_calendars 的 session_open/close 返回 UTC 时间
    - 我们在 UTC 下统一比较，避免 DST 转换问题
    - 输出给前端时转换为 US/Eastern (EST/EDT)
    """
    try:
        today = now_utc.normalize()

        # ── 检查今日是否为交易日 ──
        if not _NYSE.is_session(today.date()):
            # 非交易日 (周末或节假日)
            next_session = _NYSE.date_to_session(today, direction="next")
            next_open_utc = _NYSE.session_open(next_session)

            # 检查是否为节假日
            holiday_name = _get_holiday_name(today)

            return False, _build_status(
                is_open=False,
                now_utc=now_utc,
                next_open_utc=next_open_utc,
                holiday_name=holiday_name,
            )

        # ── 今日是交易日 → 获取开/闭盘时间 ──
        session_date = _NYSE.date_to_session(today, direction="none")
        open_utc = _NYSE.session_open(session_date)
        close_utc = _NYSE.session_close(session_date)

        # 判断是否为提前闭盘日 (正常 16:00 EST = 21:00 UTC，提前收盘 13:00 EST = 18:00 UTC)
        is_early = _is_early_close(session_date)

        if open_utc <= now_utc <= close_utc:
            # ── 在交易时段内 ──
            return True, _build_status(
                is_open=True,
                now_utc=now_utc,
                next_close_utc=close_utc,
                is_early_close=is_early,
            )
        else:
            # ── 盘前或盘后 ──
            if now_utc < open_utc:
                # 盘前
                return False, _build_status(
                    is_open=False,
                    now_utc=now_utc,
                    next_open_utc=open_utc,
                    next_close_utc=close_utc,
                    is_early_close=is_early,
                )
            else:
                # 盘后 → 找下一个交易日
                next_session = _NYSE.date_to_session(today + pd.Timedelta(days=1), direction="next")
                next_open_utc = _NYSE.session_open(next_session)
                return False, _build_status(
                    is_open=False,
                    now_utc=now_utc,
                    next_open_utc=next_open_utc,
                )

    except Exception as e:
        logger.error(f"Calendar check error: {e}")
        # 异常时安全放行
        return True, {"is_open": True, "error": str(e)}


def _build_status(
    is_open: bool,
    now_utc: pd.Timestamp,
    next_open_utc: pd.Timestamp | None = None,
    next_close_utc: pd.Timestamp | None = None,
    is_early_close: bool = False,
    holiday_name: str | None = None,
) -> dict:
    """构建 CalendarStatus 字典 — 时间转换为 US/Eastern"""
    eastern = "US/Eastern"

    result = {
        "is_open": is_open,
        "current_time_est": str(now_utc.tz_convert(eastern)),
        "is_early_close": is_early_close,
    }

    if next_open_utc is not None:
        result["next_open"] = str(next_open_utc.tz_convert(eastern))
    if next_close_utc is not None:
        result["next_close"] = str(next_close_utc.tz_convert(eastern))
    if holiday_name:
        result["holiday_name"] = holiday_name

    return result


def _is_early_close(session_date: pd.Timestamp) -> bool:
    """
    判断是否为提前闭盘日

    NYSE 提前闭盘日通常在 13:00 EST 收盘:
    - 7月3日 (独立日前夕)
    - 11月感恩节后第一天 (Black Friday)
    - 12月24日 (圣诞前夕)
    """
    try:
        close = _NYSE.session_close(session_date)
        # 正常收盘 21:00 UTC (16:00 EST) / 20:00 UTC (夏令时 16:00 EDT)
        # 提前收盘 18:00 UTC (13:00 EST) / 17:00 UTC (13:00 EDT)
        # 判断: 如果收盘时间早于 19:00 UTC，认为是提前收盘
        return close.hour < 19
    except Exception:
        return False


def _get_holiday_name(date: pd.Timestamp) -> str | None:
    """尝试获取节假日名称 (从 exchange_calendars 的 adhoc_holidays)"""
    try:
        # exchange_calendars 没有直接暴露节假日名称的 API
        # 通过日期匹配常见节日
        md = (date.month, date.day)
        holidays = {
            (1, 1): "New Year's Day",
            (1, 2): "New Year's Day (observed)",
            (7, 4): "Independence Day",
            (12, 25): "Christmas Day",
        }
        if md in holidays:
            return holidays[md]

        # Martin Luther King Jr. Day, Presidents' Day 等浮动节日难以硬编码
        # 简化: 如果是非交易日且非周末，标记为 "Market Holiday"
        if date.dayofweek < 5:  # 工作日但非交易日 = 节假日
            return "Market Holiday"
        return None
    except Exception:
        return None
