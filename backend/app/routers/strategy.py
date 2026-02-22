"""
Strategy 信号 & 执行路由 — 全量数据大一统 + 幂等发单

GET  /api/v1/strategy/signal?ticker=SPY  → 全量信号数据 (统一 JSON 契约)
POST /api/v1/strategy/execute             → 幂等发单 (Redis SETNX + BackgroundTasks)
GET  /api/v1/strategy/order/{order_id}    → 订单状态轮询
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.adapters.yahoo import YahooFinanceAdapter
from app.risk.dynamic_thresholds import calculate_dynamic_risk_params
from app.schemas.strategy import ProjectionRequest, ProjectionResponse, StrategyMarketContext, TimingDecision
from app.services.fundamental_data import get_fundamental_context
from app.services.scenario_calculator import calculate_buy_write_scenario
from app.services.strategy_entry import evaluate_market_entry
from app.services.strategy_timing import StrategyTimingService

logger = logging.getLogger("alphatheta.router.strategy")
router = APIRouter()

_yahoo = YahooFinanceAdapter()
_svc = StrategyTimingService()

# ── 幂等锁 (内存版, 生产用 Redis SETNX) ──
_idempotency_store: dict[str, dict] = {}

# ── 订单状态 (内存版, 生产用 DB) ──
_order_store: dict[str, dict] = {}


# ══════════════════════════════════════════════════════════════════
# GET /signal — 全量信号数据 (统一 JSON 契约)
# ══════════════════════════════════════════════════════════════════

@router.get("/signal")
async def get_unified_signal(ticker: str = Query("SPY", max_length=10)):
    """
    全量信号端点 — 前端信号页唯一数据源

    返回严格遵循 Data Contract 的 JSON 结构:
    所有字段保证存在, 缺失数据用 null / "N/A" / 0 填充
    """
    try:
        # ── 并行拉数据 (行情 + 基本面) — 15s 超时防卡死 ──
        try:
            quote, indicators, fundamental = await asyncio.wait_for(
                asyncio.gather(
                    _yahoo.get_quote(ticker),
                    _yahoo.get_indicators(ticker),
                    get_fundamental_context(ticker),
                ),
                timeout=15.0,
            )
            vix_val = await asyncio.wait_for(_yahoo.get_vix(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning(f"yfinance timeout for {ticker}, using fallback")
            return _fallback_signal(ticker, "yfinance timeout — market may be closed")
        current_price = quote.last or 0

        rsi_14 = indicators.get("rsi_14", 50.0)
        sma200 = indicators.get("sma200", 0)
        sma200_dist = indicators.get("sma200_distance", 0)
        atr_14 = indicators.get("atr_14", current_price * 0.015)

        # ── AI 决策 ──
        ctx = StrategyMarketContext(
            ticker=ticker,
            underlying_price=current_price,
            vix=vix_val,
            rsi_14=rsi_14,
            has_position=False,
            current_position_qty=0,
            available_cash=45000.0,
        )
        decision: TimingDecision = evaluate_market_entry(ctx)

        # ── 执行参数 ──
        strike = round(current_price * 1.02, 2) if current_price > 0 else 525.0
        premium = 5.20
        dte = 30
        net_cost = round((current_price - premium) * 100, 2)

        # ── 情景推演 ──
        scenario = calculate_buy_write_scenario(
            stock_price=current_price, strike=strike,
            premium=premium, dte=dte,
        )

        # ── 动态风控 ──
        iv_est = vix_val / 100.0
        risk_params = calculate_dynamic_risk_params(
            ticker=ticker, strategy_type="buy_write",
            current_price=current_price, iv=iv_est,
            atr_14=atr_14, dte=dte,
            strike=strike, premium=premium,
        )

        # ── 组装统一 JSON 契约 ──
        action_type = "hold"
        if decision.action_type:
            at = decision.action_type.value if hasattr(decision.action_type, 'value') else str(decision.action_type)
            if "write" in at.lower() or "buy" in at.lower():
                action_type = "buy-write"
            elif "put" in at.lower() or "sell" in at.lower():
                action_type = "sell-put"
            else:
                action_type = at.lower().replace(" ", "-")

        # 基本面摘要
        pe_display = fundamental.forward_pe or fundamental.trailing_pe or None
        cap_display = _format_cap(fundamental.market_cap)
        earnings_display = str(fundamental.earnings_date) if fundamental.earnings_date else None
        exdiv_display = str(fundamental.ex_dividend_date) if fundamental.ex_dividend_date else None

        # SMA200 状态文本
        if sma200 > 0 and current_price > 0:
            if sma200_dist >= 0:
                sma_status = f"高于 200 日均线 +{sma200_dist:.1f}%"
            else:
                sma_status = f"低于 200 日均线 {sma200_dist:.1f}%"
        else:
            sma_status = "N/A"

        return {
            "ticker": ticker,
            "current_price": current_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),

            "signal": {
                "action_type": action_type,
                "confidence": decision.confidence or 0.75,
                "scene_label": decision.scene_label or "N/A",
                "reasoning": decision.reasoning or "",
                "execution": {
                    "strike": strike,
                    "expiration_date": "2026-04-03",
                    "premium": premium,
                    "quantity_stock": 100,
                    "quantity_option": 1,
                    "net_cost": net_cost,
                    "dte": dte,
                },
            },

            "ai_reasons": {
                "fundamental": {
                    "pe_ratio": round(pe_display, 1) if pe_display else None,
                    "market_cap": cap_display,
                    "market_cap_label": fundamental.market_cap_label,
                    "earnings_date": earnings_display,
                    "ex_dividend_date": exdiv_display,
                    "dividend_yield": fundamental.dividend_yield,
                    "recommendation": fundamental.recommendation_label,
                    "diagnosis": fundamental.diagnosis,
                },
                "technical": {
                    "rsi_14": round(rsi_14, 1),
                    "sma200": round(sma200, 2) if sma200 else None,
                    "sma200_status": sma_status,
                    "sma200_distance": round(sma200_dist, 2),
                    "vix": round(vix_val, 1),
                },
                "scenario": {
                    "strategy": scenario.strategy,
                    "break_even": scenario.break_even,
                    "max_profit": scenario.max_profit,
                    "annualized_roi": scenario.annualized_roi,
                    "up_scenario": scenario.scenarios[0].description if scenario.scenarios else "",
                    "down_scenario": scenario.scenarios[-1].description if scenario.scenarios else "",
                    "summary": scenario.summary,
                    "scenarios": [
                        {
                            "label": s.label, "icon": s.icon,
                            "description": s.description,
                            "pnl": round(s.pnl, 2),
                            "pnl_pct": round(s.pnl_pct, 1),
                            "color": s.color,
                        }
                        for s in scenario.scenarios
                    ],
                },
            },

            "risk_scenarios": [
                {
                    "title": s.scenario_name,
                    "trigger": s.trigger_condition,
                    "action": s.action_plan,
                    "tag_type": s.tag_type,
                    "threshold_price": s.threshold_price,
                    "priority": s.priority,
                }
                for s in risk_params.scenarios
            ],

            "risk_summary": {
                "implied_move_1sigma": risk_params.implied_move_1sigma,
                "implied_move_2sigma": risk_params.implied_move_2sigma,
                "atr_stop_loss": risk_params.atr_stop_loss,
                "upside_1sigma": risk_params.upside_1sigma,
                "downside_1sigma": risk_params.downside_1sigma,
            },
        }

    except Exception as e:
        logger.exception(f"Signal endpoint error: {e}")
        return _fallback_signal(ticker, str(e))


# ══════════════════════════════════════════════════════════════════
# POST /execute — 幂等发单
# ══════════════════════════════════════════════════════════════════

class ExecuteRequest(BaseModel):
    """发单请求"""
    ticker: str = Field(..., max_length=10)
    action_type: str = Field(..., description="buy-write / sell-put")
    strike: float = Field(..., ge=0)
    premium: float = Field(..., ge=0)
    quantity: int = Field(default=1, ge=1, le=10)


@router.post("/execute")
async def execute_order(
    req: ExecuteRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
):
    """
    幂等发单 — 防连点

    流程:
    1. 检查 Idempotency-Key → 已存在则返回 409
    2. 生成 order_id → 存入幂等锁
    3. 推入 BackgroundTasks → Price Walking
    4. 立即返回 { status: "processing", order_id }
    """
    # 若无 key, 自动生成 (但前端应该总是传)
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    # ── 幂等校验 (生产用 Redis SETNX, TTL=30s) ──
    if idempotency_key in _idempotency_store:
        existing = _idempotency_store[idempotency_key]
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Duplicate request",
                "order_id": existing.get("order_id"),
                "message": "该订单已提交，请勿重复点击",
            },
        )

    # ── 生成 order ──
    order_id = str(uuid.uuid4())
    _idempotency_store[idempotency_key] = {
        "order_id": order_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _order_store[order_id] = {
        "order_id": order_id,
        "status": "processing",
        "ticker": req.ticker,
        "action_type": req.action_type,
        "strike": req.strike,
        "premium": req.premium,
        "quantity": req.quantity,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "filled_at": None,
        "fill_price": None,
    }

    # ── 后台执行 Price Walking ──
    background_tasks.add_task(_simulate_price_walking, order_id, req)

    logger.info(f"[Execute] Order {order_id} submitted for {req.ticker} {req.action_type}")

    return {
        "status": "processing",
        "order_id": order_id,
        "idempotency_key": idempotency_key,
        "message": "订单已提交，正在执行智能路由...",
    }


@router.get("/order/{order_id}")
async def get_order_status(order_id: str):
    """订单状态轮询"""
    order = _order_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ══════════════════════════════════════════════════════════════════
# 保留原有接口
# ══════════════════════════════════════════════════════════════════

@router.post("/timing", response_model=TimingDecision)
async def evaluate_timing(
    ticker: str = "SPY",
    rsi_14: float = 55,
    vix: float = 18.5,
    position: str = "100 shares",
    call_strike: float = 525,
    call_premium: float = 6.70,
    put_strike: float = 505,
    put_premium: float = 3.80,
):
    """择时决策树 — 输出最优单一操作"""
    return _svc.evaluate_timing(
        rsi_14=rsi_14, vix=vix, position=position, ticker=ticker,
        call_strike=call_strike, call_premium=call_premium,
        put_strike=put_strike, put_premium=put_premium,
    )


@router.post("/project", response_model=ProjectionResponse)
async def calculate_projection(req: ProjectionRequest):
    """沙盒推演计算器"""
    return _svc.calculate_projection(req)


# ══════════════════════════════════════════════════════════════════
# 内部工具函数
# ══════════════════════════════════════════════════════════════════

async def _simulate_price_walking(order_id: str, req: ExecuteRequest):
    """模拟 Price Walking 后台任务 (生产替换为 SmartOrderRouter)"""
    await asyncio.sleep(5)  # 模拟 5 秒成交延迟
    order = _order_store.get(order_id)
    if order:
        order["status"] = "filled"
        order["filled_at"] = datetime.now(timezone.utc).isoformat()
        order["fill_price"] = req.premium
        logger.info(f"[Execute] Order {order_id} FILLED @ ${req.premium}")


def _format_cap(cap: float) -> str:
    """格式化市值"""
    if cap >= 1e12:
        return f"${cap / 1e12:.1f}T"
    elif cap >= 1e9:
        return f"${cap / 1e9:.1f}B"
    elif cap >= 1e6:
        return f"${cap / 1e6:.0f}M"
    return f"${cap:,.0f}"


def _fallback_signal(ticker: str, error: str) -> dict:
    """故障降级 — 保证 JSON 契约结构完整"""
    return {
        "ticker": ticker,
        "current_price": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": error,
        "signal": {
            "action_type": "hold",
            "confidence": 0,
            "scene_label": "Error",
            "reasoning": f"数据获取失败: {error}",
            "execution": {
                "strike": 0, "expiration_date": None,
                "premium": 0, "quantity_stock": 0,
                "quantity_option": 0, "net_cost": 0, "dte": 0,
            },
        },
        "ai_reasons": {
            "fundamental": {
                "pe_ratio": None, "market_cap": "N/A",
                "market_cap_label": "N/A", "earnings_date": None,
                "ex_dividend_date": None, "dividend_yield": 0,
                "recommendation": "N/A", "diagnosis": [],
            },
            "technical": {
                "rsi_14": 0, "sma200": None,
                "sma200_status": "N/A", "sma200_distance": 0,
                "vix": 0,
            },
            "scenario": {
                "strategy": "N/A", "break_even": 0,
                "max_profit": 0, "annualized_roi": 0,
                "up_scenario": "", "down_scenario": "",
                "summary": "", "scenarios": [],
            },
        },
        "risk_scenarios": [],
        "risk_summary": {
            "implied_move_1sigma": 0, "implied_move_2sigma": 0,
            "atr_stop_loss": 0, "upside_1sigma": 0, "downside_1sigma": 0,
        },
    }
