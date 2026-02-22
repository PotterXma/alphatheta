"""
Dashboard 聚合 API — 真实行情 + 策略引擎 AI 预测 + 基本面 + 情景推演

一次请求完成:
  1. 从 yfinance 拉取 SPY/QQQ/^VIX 真实行情
  2. 计算 SMA200, RSI-14 技术指标
  3. 抓取基本面数据 (PE, 市值, 分析师评级)
  4. 组装 StrategyMarketContext → 调用 AI 决策树
  5. 计算 Buy-Write 情景盈亏推演
  6. 打包返回给前端
"""

import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter

from app.adapters.yahoo import YahooFinanceAdapter
from app.schemas.strategy import OptionContract, StrategyMarketContext, TimingDecision
from app.services.fundamental_data import get_fundamental_context
from app.services.scenario_calculator import calculate_buy_write_scenario
from app.services.strategy_entry import evaluate_market_entry
from app.risk.dynamic_thresholds import calculate_dynamic_risk_params
from app.db.session import get_async_session
from app.models.watchlist import WatchlistTicker
from sqlalchemy import select

logger = logging.getLogger("alphatheta.router.dashboard")
router = APIRouter()

_yahoo = YahooFinanceAdapter()

# ── 默认 fallback 票池 (DB 为空时使用) ──
_DEFAULT_POOL = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN"]


async def _get_active_tickers() -> list[str]:
    """从 DB 查询活跃标的列表, fallback 到默认池"""
    try:
        async with get_async_session() as session:
            result = await session.execute(
                select(WatchlistTicker.ticker)
                .where(WatchlistTicker.is_active == True)
                .order_by(WatchlistTicker.ticker)
            )
            tickers = [r[0] for r in result.all()]
            return tickers if tickers else _DEFAULT_POOL
    except Exception as e:
        logger.warning(f"DB watchlist query failed, using defaults: {e}")
        return _DEFAULT_POOL


@router.get("/sync")
async def dashboard_sync():
    """
    Dashboard 全量同步接口 — 前端唯一数据源

    返回 JSON:
    {
        "market": { vix, spy, qqq },
        "signal": { action_type, scene_label, reasoning, ai_reasons },
        "fundamentals": { diagnosis, forward_pe, recommendation_label },
        "scenario": { break_even, max_profit, max_loss, scenarios },
        "portfolio": { totalValue, cash, marginUsed },
    }
    """
    try:
        # ── Step 1: 并行拉取行情 + 基本面 + 期权链 ──
        spy_quote, qqq_quote, vix_val, spy_indicators, fundamental, spy_chain_raw = await asyncio.gather(
            _yahoo.get_quote("SPY"),
            _yahoo.get_quote("QQQ"),
            _yahoo.get_vix(),
            _yahoo.get_indicators("SPY"),
            get_fundamental_context("SPY"),
            _yahoo.get_option_chain("SPY"),
        )

        rsi_14 = spy_indicators.get("rsi_14", 50.0)
        sma200 = spy_indicators.get("sma200", 0.0)
        sma200_dist = spy_indicators.get("sma200_distance", 0.0)

        # ── Step 2: 转换期权链为 OptionContract 列表 ──
        options_chain = []
        for c in spy_chain_raw:
            try:
                options_chain.append(OptionContract(**c))
            except Exception:
                pass  # 跳过格式不合规的合约
        logger.info(f"📋 SPY chain: {len(options_chain)} valid contracts")

        # ── Step 3: 组装策略引擎输入 (含真实期权链) ──
        # 防御: yfinance 偶发 None 返回 → spy_quote.last = 0
        spot_price = spy_quote.last if spy_quote and spy_quote.last > 0 else 0
        if spot_price == 0:
            logger.warning("SPY quote returned 0 — skipping strategy engine, using fallback")
            raise ValueError("SPY quote unavailable")

        strategy_ctx = StrategyMarketContext(
            ticker="SPY",
            underlying_price=spot_price,
            vix=vix_val,
            rsi_14=rsi_14,
            has_position=False,
            current_position_qty=0,
            available_cash=45000.0,
            options_chain=options_chain,
        )

        # ── Step 4: AI 决策 (期权链寻优: Δ≈0.16) ──
        decision: TimingDecision = evaluate_market_entry(strategy_ctx)

        # ── Step 5: 情景盈亏推演 (使用真实期权参数) ──
        # 优先用策略引擎从期权链中寻优的真实 strike/premium
        exec_d = decision.execution_details
        if exec_d and exec_d.strike_price > 0:
            strike = exec_d.strike_price
            premium = exec_d.estimated_premium or exec_d.limit_price or 5.20
            dte = exec_d.dte or 30
        else:
            # fallback: 计算近似值
            strike = round(spy_quote.last * 1.02, 2)
            premium = 5.20
            dte = 30

        scenario = calculate_buy_write_scenario(
            stock_price=spy_quote.last,
            strike=strike,
            premium=premium,
            dte=dte,
        )

        # ── Step 5: 构建 AI 理由数组 (基本面+技术面+情景) ──
        ai_reasons = []

        # 基本面理由
        ai_reasons.extend(fundamental.diagnosis)

        # 技术面理由
        ai_reasons.append(f"RSI-14: {rsi_14:.1f}")
        if sma200 > 0:
            ai_reasons.append(
                f"SPY 距 SMA200 ({sma200:.2f}): "
                f"{'▲' if sma200_dist >= 0 else '▼'}{abs(sma200_dist):.2f}%"
            )
        ai_reasons.append(f"VIX: {vix_val:.1f}")

        # 基本面过滤逻辑
        if fundamental.forward_pe and fundamental.forward_pe > 100 and rsi_14 > 60:
            ai_reasons.append("🚫 估值过高 (PE>100) 且技术超买 (RSI>60) — 拒绝建仓")

        # ── Step 6: 序列化 ──
        action_val = decision.action_type.value if hasattr(decision.action_type, 'value') else str(decision.action_type)
        _stock_actions = {
            "sell_put": "🚫 不买正股 — 仅卖出 Put 收取权利金。若被行权则以行权价接盘正股",
            "sell_call": "📦 持有正股 — 已持有 100 股, 卖出备兑 Call 降低持仓成本",
            "buy_write": f"🛒 买入 100 股 {decision.target_ticker} @ ${spot_price:.2f} + 同时卖出 1 张 OTM Call 降低成本",
            "hold": "⏸ 观望 — 当前不建议买入或卖出正股",
        }
        signal_data = {
            "action_type": action_val,
            "target_ticker": decision.target_ticker,
            "scene_label": decision.scene_label,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "ai_reasons": ai_reasons,
            "stock_action": _stock_actions.get(action_val.lower(), "⏸ 观望"),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

        if decision.execution_details:
            ed = decision.execution_details
            signal_data["execution_details"] = {
                "contract_symbol": ed.contract_symbol,
                "strike_price": ed.strike_price,
                "expiration": ed.expiration,
                "estimated_premium": ed.estimated_premium,
                "actual_delta": ed.actual_delta,
                "target_delta": ed.target_delta,
                "dte": ed.dte,
                "limit_price": ed.limit_price,
                "open_interest": ed.open_interest,
                "volume": ed.volume,
            }

        # 序列化 scenario
        scenario_data = {
            "strategy": scenario.strategy,
            "break_even": scenario.break_even,
            "max_profit": scenario.max_profit,
            "max_loss": scenario.max_loss,
            "net_investment": scenario.net_investment,
            "annualized_roi": scenario.annualized_roi,
            "summary": scenario.summary,
            "scenarios": [
                {
                    "label": s.label,
                    "icon": s.icon,
                    "description": s.description,
                    "pnl": round(s.pnl, 2),
                    "pnl_pct": round(s.pnl_pct, 1),
                    "color": s.color,
                }
                for s in scenario.scenarios
            ],
        }

        # ── Step 6: 动态风控参数 (ATR/IV 自适应) ──
        atr_14 = spy_indicators.get("atr_14", spy_quote.last * 0.015)  # fallback: 1.5% 日波动
        iv_estimate = vix_val / 100.0  # VIX 近似 SPY IV
        risk_params = calculate_dynamic_risk_params(
            ticker="SPY",
            strategy_type="buy_write",
            current_price=spy_quote.last,
            iv=iv_estimate,
            atr_14=atr_14,
            dte=dte,
            strike=strike,
            premium=premium,
        )
        risk_data = {
            "ticker": risk_params.ticker,
            "strategy_type": risk_params.strategy_type,
            "current_price": risk_params.current_price,
            "implied_move_1sigma": risk_params.implied_move_1sigma,
            "implied_move_2sigma": risk_params.implied_move_2sigma,
            "atr_stop_loss": risk_params.atr_stop_loss,
            "upside_1sigma": risk_params.upside_1sigma,
            "downside_1sigma": risk_params.downside_1sigma,
            "scenarios": [
                {
                    "scenario_name": s.scenario_name,
                    "trigger_condition": s.trigger_condition,
                    "action_plan": s.action_plan,
                    "tag_type": s.tag_type,
                    "threshold_price": s.threshold_price,
                    "priority": s.priority,
                }
                for s in risk_params.scenarios
            ],
        }

        # 序列化 fundamentals
        fundamental_data = {
            "market_cap": fundamental.market_cap,
            "market_cap_label": fundamental.market_cap_label,
            "trailing_pe": fundamental.trailing_pe,
            "forward_pe": fundamental.forward_pe,
            "recommendation_label": fundamental.recommendation_label,
            "recommendation_mean": fundamental.recommendation_mean,
            "dividend_yield": fundamental.dividend_yield,
            "earnings_date": str(fundamental.earnings_date) if fundamental.earnings_date else None,
            "ex_dividend_date": str(fundamental.ex_dividend_date) if fundamental.ex_dividend_date else None,
            "diagnosis": fundamental.diagnosis,
        }

        return {
            "market": {
                "vix": vix_val,
                "spy": {
                    "price": spy_quote.last,
                    "bid": spy_quote.bid,
                    "ask": spy_quote.ask,
                    "volume": spy_quote.volume,
                    "sma200": sma200,
                    "sma200_distance": sma200_dist,
                    "rsi_14": rsi_14,
                },
                "qqq": {
                    "price": qqq_quote.last,
                    "bid": qqq_quote.bid,
                    "ask": qqq_quote.ask,
                    "volume": qqq_quote.volume,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "signal": signal_data,
            "fundamentals": fundamental_data,
            "scenario": scenario_data,
            "risk": risk_data,
            "portfolio": {
                "totalValue": 100000.00,
                "cash": 100000.00,
                "marginUsed": 0,
            },
        }

    except Exception as e:
        logger.exception(f"Dashboard sync failed: {e}")
        return {
            "market": {
                "vix": 0, "spy": {"price": 0}, "qqq": {"price": 0},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "signal": {
                "action_type": "Hold",
                "scene_label": "Error",
                "reasoning": f"行情获取失败: {str(e)}",
                "confidence": 0,
                "ai_reasons": [f"⚠ {str(e)}"],
            },
            "fundamentals": {"diagnosis": []},
            "scenario": {"scenarios": []},
            "portfolio": {"totalValue": 0, "cash": 0, "marginUsed": 0},
            "error": str(e),
        }


# ══════════════════════════════════════════════════════════════════
# GET /scan — 多标的池扫描 (遍历 watchlist, 每只跑策略引擎)
# ══════════════════════════════════════════════════════════════════

@router.get("/scan")
async def scan_watchlist():
    """
    多标的池扫描 — 遍历 watchlist, 为每只标的:
    1. 拉行情 + 技术指标 + 期权链
    2. 构建 StrategyMarketContext (含真实期权链)
    3. 运行策略引擎 (Delta 寻优)
    4. 返回按 confidence 排序的信号列表

    前端可用此接口展示 "最优信号排行榜"
    """
    vix_val = await _yahoo.get_vix()

    async def _scan_single(ticker: str) -> dict | None:
        """扫描单只标的"""
        try:
            quote, indicators, chain_raw = await asyncio.gather(
                _yahoo.get_quote(ticker),
                _yahoo.get_indicators(ticker),
                _yahoo.get_option_chain(ticker),
            )

            options_chain = []
            for c in chain_raw:
                try:
                    options_chain.append(OptionContract(**c))
                except Exception:
                    pass

            ctx = StrategyMarketContext(
                ticker=ticker,
                underlying_price=quote.last if quote and quote.last > 0 else 0.01,  # Pydantic gt=0 guard
                vix=vix_val,
                rsi_14=indicators.get("rsi_14", 50.0),
                has_position=False,
                current_position_qty=0,
                available_cash=45000.0,
                options_chain=options_chain,
            )

            decision = evaluate_market_entry(ctx)
            exec_d = decision.execution_details

            # 正股操作指引
            _stock_actions = {
                "sell_put": "🚫 不买正股 — 仅卖出 Put 收取权利金。若被行权则以行权价接盘正股",
                "sell_call": "📦 持有正股 — 已持有 100 股, 卖出备兑 Call 降低持仓成本",
                "buy_write": f"🛒 买入 100 股 {ticker} @ ${quote.last:.2f} + 同时卖出 1 张 OTM Call 降低成本",
                "hold": "⏸ 观望 — 当前不建议买入或卖出正股",
            }
            action_val = decision.action_type.value if hasattr(decision.action_type, 'value') else str(decision.action_type)

            return {
                "ticker": ticker,
                "price": quote.last,
                "rsi_14": indicators.get("rsi_14", 50.0),
                "action_type": action_val,
                "scene_label": decision.scene_label,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "stock_action": _stock_actions.get(action_val.lower(), "⏸ 观望"),
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "chain_size": len(options_chain),
                "execution": {
                    "contract": exec_d.contract_symbol if exec_d else None,
                    "strike": exec_d.strike_price if exec_d else None,
                    "delta": exec_d.actual_delta if exec_d else None,
                    "premium": exec_d.estimated_premium if exec_d else None,
                    "dte": exec_d.dte if exec_d else None,
                } if exec_d else None,
            }
        except Exception as e:
            logger.warning(f"Scan failed for {ticker}: {e}")
            return {
                "ticker": ticker,
                "price": 0,
                "action_type": "error",
                "confidence": 0,
                "reasoning": f"扫描失败: {str(e)}",
                "chain_size": 0,
            }

    # 从 DB 获取活跃标的列表
    pool = await _get_active_tickers()

    # 并行扫描所有标的
    results = await asyncio.gather(*[_scan_single(t) for t in pool])
    results = [r for r in results if r is not None]

    # 按 confidence 降序, HOLD 排最后
    results.sort(
        key=lambda r: (0 if r["action_type"] in ("Hold", "hold") else 1, r["confidence"]),
        reverse=True,
    )

    return {
        "pool": pool,
        "vix": vix_val,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "signals": results,
        "best_signal": results[0] if results else None,
    }
