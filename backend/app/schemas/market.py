"""
市场与日历数据契约 — Dashboard + 决策树共用的市场上下文

设计要点:
1. 所有时间字段使用 datetime (带时区)，确保 timezone-aware
2. vix / rsi 等指标使用 Field 约束范围
3. CalendarStatus 包含完整的开闭盘信息，供前端倒计时展示
4. data_quality 枚举标识数据可信度
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class DataQuality(StrEnum):
    """数据质量等级"""
    REALTIME = "realtime"      # 实时数据 (< 5s 延迟)
    DELAYED = "delayed"        # 延迟数据 (5~30s)
    STALE = "stale"            # 陈旧数据 (> 30s，可能不可靠)
    INSUFFICIENT = "insufficient"  # 数据不足 (无法计算指标)


class Quote(BaseModel):
    """实时报价快照"""
    ticker: str = Field(..., description="标的代码")
    bid: float = Field(..., ge=0, description="最优买价")
    ask: float = Field(..., ge=0, description="最优卖价")
    last: float = Field(..., ge=0, description="最新成交价")
    mid_price: float = Field(..., ge=0, description="中间价 (bid+ask)/2")
    spread_pct: float = Field(
        ..., ge=0,
        description="Bid/Ask 价差百分比 = (ask-bid)/ask × 100",
    )
    volume: int | None = Field(default=None, ge=0, description="成交量")
    timestamp: datetime | None = Field(default=None, description="报价时间 (UTC)")
    data_latency_seconds: float = Field(
        default=0.0, ge=0,
        description="数据延迟 (秒)，> 15s 触发 Kill Switch",
    )

    @field_validator("spread_pct")
    @classmethod
    def warn_wide_spread(cls, v: float) -> float:
        """价差超过 8% 会被 Kill Switch 拦截 — 这里仅做标注"""
        return round(v, 2)


class Indicators(BaseModel):
    """技术指标快照"""
    rsi_14: float | None = Field(
        default=None, ge=0, le=100,
        description="RSI-14 (Wilder 平滑)，0~100",
    )
    sma200: float | None = Field(
        default=None, ge=0,
        description="200 日简单移动平均线价格",
    )
    sma200_distance: float | None = Field(
        default=None,
        description="距 SMA200 的距离百分比 (正 = 高于均线)",
    )
    hv_30d: float | None = Field(
        default=None, ge=0, le=200,
        description="30 日历史波动率 (%)",
    )
    iv_rank: float | None = Field(
        default=None, ge=0, le=100,
        description="隐含波动率百分位排名 (0~100)",
    )
    data_quality: DataQuality = Field(
        default=DataQuality.REALTIME,
        description="指标数据质量等级",
    )


class MarketContext(BaseModel):
    """
    完整市场上下文 — 前端 Dashboard 和后端决策树共同依赖的数据结构

    举例: renderSignal() 需要 vix 和 rsi_14 做择时判断，
    renderCRO() 需要 spread_pct 和 data_latency 做 Kill Switch 评估。
    """
    ticker: str = Field(..., description="标的代码")

    # ── 报价 ──
    bid: float = Field(..., ge=0, description="最优买价")
    ask: float = Field(..., ge=0, description="最优卖价")
    mid_price: float = Field(..., ge=0, description="中间价")
    spread_pct: float = Field(..., ge=0, description="价差百分比 (%)")

    # ── 宏观指标 ──
    vix: float = Field(
        ..., ge=0, le=100,
        description="CBOE VIX 恐慌指数。> 35 触发 VIX Override (强制 Hold)",
    )

    # ── 技术指标 ──
    rsi_14: float | None = Field(
        default=None, ge=0, le=100,
        description="RSI-14。< 40 = 超卖 (Scene A), > 60 = 超买 (Scene B)",
    )
    sma200_distance: float | None = Field(
        default=None,
        description="距 SMA200 百分比",
    )
    hv_30d: float | None = Field(
        default=None, ge=0,
        description="30 日历史波动率 (%)",
    )
    iv_rank: float | None = Field(
        default=None, ge=0, le=100,
        description="IV Rank (%)",
    )

    # ── 资金 ──
    available_cash: float = Field(
        default=0.0, ge=0,
        description="可用现金 ($)",
    )

    # ── 数据质量 ──
    data_latency_seconds: float = Field(
        default=0.0, ge=0,
        description="数据延迟秒数。> 15s 触发 Rule 1·Stale Data",
    )
    data_quality: DataQuality = Field(
        default=DataQuality.REALTIME,
        description="数据质量等级",
    )


class CalendarStatus(BaseModel):
    """
    交易日历状态 — 供前端展示开闭盘倒计时

    所有时间为 US/Eastern 时区 (美东时间)
    """
    is_open: bool = Field(
        ...,
        description="当前是否在交易时段内",
    )
    current_time_est: datetime = Field(
        ...,
        description="当前美东时间 (timezone-aware)",
    )
    next_open: datetime | None = Field(
        default=None,
        description="下一次开盘时间 (美东)。已开盘时为 None",
    )
    next_close: datetime | None = Field(
        default=None,
        description="下一次收盘时间 (美东)。已收盘时为 None",
    )
    is_early_close: bool = Field(
        default=False,
        description="今日是否为提前收盘日 (如圣诞前夕 13:00 EST 收盘)",
    )
    holiday_name: str | None = Field(
        default=None,
        description="如为节假日休市，显示节日名称",
    )
