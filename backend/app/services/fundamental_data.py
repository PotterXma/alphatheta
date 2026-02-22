"""
基本面数据服务 — yfinance 抓取 + 异常兜底

抓取关键因子:
- marketCap (市值) → 判断市场地位 (Large/Mid/Small Cap)
- trailingPE / forwardPE → 判断估值水平
- epsForward → 预测每股收益
- earningsDates → 财报日 (3天内强制 HOLD, 规避 IV Crush)
- ex_dividend_date → 除息日 (Short Call 提前指派风险)
- recommendationMean → 华尔街分析师综合评级 (1=强买, 5=卖出)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime

logger = logging.getLogger("alphatheta.fundamentals")


@dataclass
class FundamentalContext:
    """基本面上下文 — 策略引擎决策输入"""
    ticker: str

    # ── 估值 ──
    market_cap: float = 0.0             # 市值 (美元)
    market_cap_label: str = "Unknown"   # Large Cap / Mid Cap / Small Cap
    trailing_pe: float | None = None    # 滚动 PE (过去 12 个月)
    forward_pe: float | None = None     # 预测 PE (未来 12 个月)
    eps_forward: float | None = None    # 预测每股收益

    # ── 分析师评级 ──
    recommendation_mean: float | None = None  # 1=强买, 2=买入, 3=持有, 4=卖出, 5=强卖
    recommendation_label: str = "N/A"

    # ── 事件日历 ──
    earnings_date: date | None = None       # 下一次财报日
    ex_dividend_date: date | None = None    # 除息日
    dividend_yield: float = 0.0             # 股息率

    # ── 诊断文本 (供前端展示) ──
    diagnosis: list[str] = field(default_factory=list)


async def get_fundamental_context(ticker: str) -> FundamentalContext:
    """
    异步获取标的基本面数据

    使用 asyncio.to_thread 包装 yfinance 同步 API,
    对每个字段做 None 兜底, 绝不因缺失字段崩溃
    """
    ctx = FundamentalContext(ticker=ticker)

    try:
        data = await asyncio.to_thread(_fetch_yfinance_info, ticker)
        if not data:
            ctx.diagnosis.append("⚠ 基本面数据获取失败")
            return ctx

        # ── 市值 ──
        ctx.market_cap = data.get("marketCap") or 0.0
        if ctx.market_cap >= 200_000_000_000:
            ctx.market_cap_label = "Mega Cap"
        elif ctx.market_cap >= 10_000_000_000:
            ctx.market_cap_label = "Large Cap"
        elif ctx.market_cap >= 2_000_000_000:
            ctx.market_cap_label = "Mid Cap"
        else:
            ctx.market_cap_label = "Small Cap"

        # ── PE 估值 ──
        ctx.trailing_pe = data.get("trailingPE")
        ctx.forward_pe = data.get("forwardPE")
        ctx.eps_forward = data.get("epsForward") or data.get("forwardEps")

        # ── 分析师评级 ──
        ctx.recommendation_mean = data.get("recommendationMean")
        if ctx.recommendation_mean:
            if ctx.recommendation_mean <= 1.5:
                ctx.recommendation_label = "Strong Buy"
            elif ctx.recommendation_mean <= 2.5:
                ctx.recommendation_label = "Buy"
            elif ctx.recommendation_mean <= 3.5:
                ctx.recommendation_label = "Hold"
            elif ctx.recommendation_mean <= 4.5:
                ctx.recommendation_label = "Sell"
            else:
                ctx.recommendation_label = "Strong Sell"

        # ── 除息日 ──
        ex_div_raw = data.get("exDividendDate")
        if ex_div_raw:
            if isinstance(ex_div_raw, (int, float)):
                ctx.ex_dividend_date = datetime.fromtimestamp(ex_div_raw).date()
            elif isinstance(ex_div_raw, str):
                ctx.ex_dividend_date = datetime.fromisoformat(ex_div_raw).date()

        ctx.dividend_yield = data.get("dividendYield") or 0.0

        # ── 财报日 ──
        # yfinance 的 earningsDate 可能是 Timestamp 或列表
        earnings_raw = data.get("earningsDate")
        if earnings_raw:
            if isinstance(earnings_raw, list) and len(earnings_raw) > 0:
                ctx.earnings_date = _parse_date(earnings_raw[0])
            else:
                ctx.earnings_date = _parse_date(earnings_raw)

        # ── 生成诊断文本 ──
        ctx.diagnosis = _build_diagnosis(ctx)

    except Exception as e:
        logger.error(f"[Fundamentals] Error fetching {ticker}: {e}")
        ctx.diagnosis.append(f"⚠ 基本面获取异常: {str(e)[:100]}")

    return ctx


def _fetch_yfinance_info(ticker: str) -> dict:
    """同步拉取 yfinance Ticker.info (包装为 to_thread 调用)"""
    import yfinance as yf
    t = yf.Ticker(ticker)
    return t.info or {}


def _parse_date(val) -> date | None:
    """安全解析日期 — 兼容 Timestamp, int, str"""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val).date()
        if hasattr(val, "date"):
            return val.date()
        if isinstance(val, str):
            return datetime.fromisoformat(val).date()
    except Exception:
        pass
    return None


def _build_diagnosis(ctx: FundamentalContext) -> list[str]:
    """根据基本面数据生成诊断标签 (供前端展示)"""
    diag = []

    # 市值
    cap_str = _format_market_cap(ctx.market_cap)
    diag.append(f"市值 {cap_str} ({ctx.market_cap_label})")

    # PE 估值
    if ctx.forward_pe is not None:
        if ctx.forward_pe > 100:
            diag.append(f"⚠ Forward PE: {ctx.forward_pe:.1f} — 估值极度偏高")
        elif ctx.forward_pe > 40:
            diag.append(f"Forward PE: {ctx.forward_pe:.1f} — 高估值成长股")
        elif ctx.forward_pe > 15:
            diag.append(f"Forward PE: {ctx.forward_pe:.1f} — 估值合理")
        else:
            diag.append(f"Forward PE: {ctx.forward_pe:.1f} — 低估值/价值股")
    elif ctx.trailing_pe is not None:
        diag.append(f"Trailing PE: {ctx.trailing_pe:.1f}")

    # 分析师评级
    if ctx.recommendation_label != "N/A":
        diag.append(f"华尔街评级: {ctx.recommendation_label}")

    # 股息
    if ctx.dividend_yield > 0:
        diag.append(f"股息率: {ctx.dividend_yield:.2f}%")

    # 事件日历
    today = date.today()
    if ctx.earnings_date:
        days_to_earnings = (ctx.earnings_date - today).days
        if 0 <= days_to_earnings <= 3:
            diag.append(f"🚨 财报日 {ctx.earnings_date} (仅剩 {days_to_earnings} 天 — IV Crush 风险)")
        elif 0 <= days_to_earnings <= 14:
            diag.append(f"📅 财报日 {ctx.earnings_date} ({days_to_earnings} 天后)")

    if ctx.ex_dividend_date:
        days_to_exdiv = (ctx.ex_dividend_date - today).days
        if 0 <= days_to_exdiv <= 3:
            diag.append(f"🚨 除息日 {ctx.ex_dividend_date} (仅剩 {days_to_exdiv} 天 — 提前指派风险)")
        elif 0 <= days_to_exdiv <= 14:
            diag.append(f"📅 除息日 {ctx.ex_dividend_date} ({days_to_exdiv} 天后)")

    return diag


def _format_market_cap(cap: float) -> str:
    """格式化市值: 1.5T / 200B / 5.3B"""
    if cap >= 1_000_000_000_000:
        return f"${cap / 1_000_000_000_000:.1f}T"
    elif cap >= 1_000_000_000:
        return f"${cap / 1_000_000_000:.1f}B"
    elif cap >= 1_000_000:
        return f"${cap / 1_000_000:.0f}M"
    return f"${cap:,.0f}"
