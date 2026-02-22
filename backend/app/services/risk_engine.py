"""风控引擎服务 — 7条 Kill Switch + 年化收益 + 执行方案 + 情景剧本"""

import logging

from app.schemas.risk import (
    ExecutionPlan,
    RiskAssessment,
    ScenarioPlaybook,
    TradeProposal,
)

logger = logging.getLogger("alphatheta.risk_engine")


class RiskEngine:
    """后端 CRO 风控评估器 — evaluateTradeProposal 的服务端实现"""

    def evaluate(self, proposal: TradeProposal, data_latency: float = 0.0) -> RiskAssessment:
        """
        执行 7 条 Kill Switch 规则，顺序评估，首个触发即否决。
        通过后生成执行方案和情景剧本。
        """

        def reject(reason: str) -> RiskAssessment:
            logger.warning(f"Risk REJECTED: {reason}")
            return RiskAssessment(is_approved=False, rejection_reason=reason)

        # ── Rule 1: 数据陈旧 ──
        if data_latency > 15:
            return reject(f"[Rule 1·Stale Data] 数据延迟 {data_latency:.1f}s > 15s")

        # ── Rule 2: Margin 利用率 ──
        if proposal.projected_margin_util > 60:
            return reject(f"[Rule 2·Margin] 预计 Margin {proposal.projected_margin_util:.0f}% > 60%")

        # ── Rule 3: 价差过大 ──
        spread_pct = (proposal.ask - proposal.bid) / proposal.ask * 100 if proposal.ask > 0 else 0
        if spread_pct > 8:
            return reject(f"[Rule 3·Spread] Bid/Ask 价差 {spread_pct:.1f}% > 8%")

        # ── Rule 4: DTE 过短 ──
        if proposal.dte < 7:
            return reject(f"[Rule 4·DTE] 到期天数 {proposal.dte} < 7")

        # ── Rule 5: Wash Sale 风险 ──
        if proposal.is_wash_sale_risk:
            return reject("[Rule 5·Wash Sale] 30天内有同标的亏损卖出，触发 Wash Sale 风险")

        # ── Rule 6: Gamma Trap ──
        # HV 显著高于 IV 且 DTE < 14 → 高 Gamma 风险
        # (简化: 使用 gamma 值直接判断)
        if proposal.gamma > 0.05 and proposal.dte < 14:
            return reject(f"[Rule 6·Gamma Trap] Gamma={proposal.gamma:.3f} 过高且 DTE={proposal.dte}")

        # ── Rule 7: 税后收益率不达标 ──
        mid_price = (proposal.bid + proposal.ask) / 2
        gross_yield = (mid_price / proposal.strike) * (365 / proposal.dte) * 100 if proposal.strike > 0 and proposal.dte > 0 else 0
        net_yield = gross_yield * (1 - proposal.est_tax_drag)

        if net_yield < 5 or net_yield > 15:
            return reject(f"[Rule 7·Yield] 税后净年化 {net_yield:.1f}% 不在 5%-15% 区间")

        # ── 全部通过 → 生成执行方案 ──
        spread = proposal.ask - proposal.bid
        starting_limit = round(mid_price, 2)
        floor_limit = round(proposal.bid + spread * 0.2, 2)

        plan = ExecutionPlan(
            recommended_order_type="Limit_Price_Chaser",
            starting_limit_price=starting_limit,
            floor_limit_price=floor_limit,
            gross_annualized_yield_est=round(gross_yield, 2),
            net_annualized_yield_after_tax=round(net_yield, 2),
        )

        # ── 情景剧本 ──
        price = proposal.strike  # 用 strike 作为标的参考价
        playbooks = [
            ScenarioPlaybook(
                title="📈 Bullish Surge (+15%)",
                scenario="标的价格突然暴涨 15%",
                action="期权大概率被行权，以 Strike 价格卖出股票。锁定收益 = Strike + 权利金",
                target_price=round(price * 1.15, 2),
            ),
            ScenarioPlaybook(
                title="📉 Bearish Crash (-20%)",
                scenario="标的价格下跌 20%",
                action="期权作废，持有股票。权利金提供缓冲垫，实际亏损 = 跌幅 - 权利金",
                target_price=round(price * 0.80, 2),
            ),
            ScenarioPlaybook(
                title="🌊 Whipsaw / Gamma Trap",
                scenario="价格剧烈波动后回归原位",
                action="持续持有，Theta 衰减对我们有利。如波动率骤升，可考虑提前平仓",
            ),
        ]

        logger.info(f"Risk APPROVED: {proposal.ticker} yield={net_yield:.1f}%")
        return RiskAssessment(
            is_approved=True,
            execution_plan=plan,
            scenario_playbooks=playbooks,
            ui_rationale=[
                f"7 条 Kill Switch 全部通过",
                f"税后净年化收益 {net_yield:.1f}% (目标 5%-15%)",
                f"建议限价 ${starting_limit} → 底线 ${floor_limit}",
            ],
        )
