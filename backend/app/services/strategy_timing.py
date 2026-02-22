"""
策略择时服务 — 4场景决策树 + 沙盒推演 + 公司行动 + Pin Risk

注: 此文件为 legacy wrapper, 保留原有 API 端点的兼容性
新代码应直接使用 strategy_entry.py 的 StrategyEntryEngine
"""

import logging

from app.schemas.strategy import (
    ActionType,
    CorporateAction,
    ExecutionDetails,
    ProjectionRequest,
    ProjectionResponse,
    StrategyMarketContext,
    TimingDecision,
)

logger = logging.getLogger("alphatheta.strategy")


class StrategyTimingService:
    """决策树引擎 + 沙盒推演 (legacy wrapper)"""

    def evaluate_timing(
        self, rsi_14: float, vix: float, position: str, ticker: str,
        call_strike: float = 0, call_premium: float = 0,
        put_strike: float = 0, put_premium: float = 0,
    ) -> TimingDecision:
        """4 场景决策树 + VIX 强制观望 (legacy API, 内部委托给新引擎)"""
        has_position = position and "0" not in position

        # Priority 0: VIX 极端恐慌
        if vix > 35:
            return TimingDecision(
                action_type=ActionType.HOLD,
                target_ticker=ticker,
                scene_label="VIX Override",
                reasoning=f"VIX={vix} 极端恐慌，暂停一切卖出策略",
            )

        # Scene A: 超卖 + 无仓位 → Sell Put
        if rsi_14 < 40 and not has_position:
            return TimingDecision(
                action_type=ActionType.SELL_PUT,
                target_ticker=ticker,
                scene_label="Scene A: Oversold",
                execution_details=ExecutionDetails(
                    strike_price=put_strike or None,
                    estimated_premium=put_premium or None,
                ),
                reasoning=f"RSI={rsi_14} 超卖，卖出 Put 收取权利金",
            )

        # Scene B: 超买 + 有仓位 → Sell Call
        if rsi_14 > 60 and has_position:
            return TimingDecision(
                action_type=ActionType.SELL_CALL,
                target_ticker=ticker,
                scene_label="Scene B: Overbought + Position",
                execution_details=ExecutionDetails(
                    strike_price=call_strike or None,
                ),
                reasoning=f"RSI={rsi_14} 多头亢奋，持仓 {position}，卖出 Call",
            )

        # Scene C: 超买 + 无仓位 → Hold
        if rsi_14 > 60 and not has_position:
            return TimingDecision(
                action_type=ActionType.HOLD,
                target_ticker=ticker,
                scene_label="Scene C: Overbought Without Position",
                reasoning=f"RSI={rsi_14} 超买但无仓位，拒绝高位追涨",
            )

        # Scene D: 震荡 + 无仓位 → Buy-Write
        if 40 <= rsi_14 <= 60 and not has_position:
            return TimingDecision(
                action_type=ActionType.BUY_WRITE,
                target_ticker=ticker,
                scene_label="Scene D: Range-Bound",
                execution_details=ExecutionDetails(
                    strike_price=call_strike or None,
                ),
                reasoning=f"RSI={rsi_14} 震荡区间，同步买入 + 卖出 Call",
            )

        # Fallback
        return TimingDecision(
            action_type=ActionType.HOLD,
            target_ticker=ticker,
            scene_label="Fallback",
            reasoning=f"RSI={rsi_14} 震荡区间，已持仓 {position}，等待更极端信号",
        )

    def calculate_projection(self, req: ProjectionRequest) -> ProjectionResponse:
        """沙盒推演计算器"""
        if req.strategy == "covered_call":
            net_cost = (req.price or 0) * req.quantity - req.premium * req.quantity
            break_even = (req.price or 0) - req.premium
            max_profit = (req.strike - (req.price or 0) + req.premium) * req.quantity
            annualized = (req.premium / (req.price or 1)) * (365 / req.dte) * 100
            return ProjectionResponse(
                net_cost=round(net_cost, 2),
                break_even=round(break_even, 2),
                max_profit=round(max_profit, 2),
                annualized_yield=round(annualized, 2),
            )

        elif req.strategy == "cash_secured_put":
            max_loss = (req.strike - req.premium) * req.quantity
            break_even = req.strike - req.premium
            max_profit_val = req.premium * req.quantity
            annualized = (req.premium / req.strike) * (365 / req.dte) * 100
            return ProjectionResponse(
                break_even=round(break_even, 2),
                max_profit=round(max_profit_val, 2),
                max_loss=round(max_loss, 2),
                annualized_yield=round(annualized, 2),
            )

        raise ValueError(f"Unknown strategy: {req.strategy}")

    def check_pin_risk(self, delta: float, dte: int) -> dict:
        """Pin Risk 检查: DTE=0 且 |delta| > 0.40 → 强平"""
        if dte == 0 and abs(delta) > 0.40:
            return {"action": "force_close", "reason": f"|delta|={abs(delta):.2f} > 0.40 on expiry day"}
        if dte == 0 and abs(delta) < 0.20:
            return {"action": "safe_expiry", "reason": f"|delta|={abs(delta):.2f} < 0.20, safe to expire"}
        return {"action": "monitor", "reason": f"DTE={dte}, delta={delta:.2f}"}

    def adjust_for_corporate_action(self, action: CorporateAction, current_strike: float) -> dict:
        """公司行动调整: 拆股/分红 → Strike 调整"""
        if action.action_type == "split" and action.ratio:
            new_strike = current_strike / action.ratio
            return {"new_strike": round(new_strike, 2), "ratio": action.ratio}
        if action.action_type == "dividend":
            return {"early_assignment_risk": True, "ex_date": action.ex_date}
        return {}
