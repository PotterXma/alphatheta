"""
生命周期巡检大脑 (Lifecycle Scanner Engine)

职责: 定期扫描所有存量持仓, 生成止盈/展期/预警信号

巡检规则 (按优先级):
┌──────────────────────────────────────────────────────────────────┐
│ Rule 1: Take-Profit (50% 动态止盈)                              │
│   Short Option 浮盈 ≥ 50% → BUY_TO_CLOSE                       │
│   金融逻辑: 权利金已拿到一半, 剩余一半需要更长时间且面临反转风险   │
│   性价比骤降, 落袋为安后可以立即重新卖出新合约 (重新开始计时)     │
├──────────────────────────────────────────────────────────────────┤
│ Rule 2: Gamma Trap (DTE ≤ 21 展期防御)                          │
│   Short Option DTE ≤ 21 且 (浮亏 或 ATM 逼近) → ROLL_OUT        │
│   金融逻辑: DTE < 21 天时 Gamma 值急剧上升 (称为 "Gamma 爆炸")   │
│   标的价格的微小波动会导致期权价格剧烈变化                       │
│   如果此时处于浮亏或 ATM 附近, 被行权风险极高                    │
│   展期到下月 = 用时间换空间, 重新获得时间价值 (Theta) 保护       │
├──────────────────────────────────────────────────────────────────┤
│ Rule 3: Deep ITM Alert (深度实值预警)                            │
│   Short Option 已深度 ITM (标的价格穿过行权价 > 5%) → ROLL_OUT   │
│   金融逻辑: 深度 ITM 的 Short Option 几乎确定会被行权            │
│   如果不想被指派 (assignment), 必须提前展期或平仓               │
└──────────────────────────────────────────────────────────────────┘

设计原则:
  - 纯函数, 无 I/O 依赖 — 输入 PositionSnapshot, 输出 TimingDecision
  - 每个规则独立, 一个持仓可触发多个信号 (由 OMS 根据优先级执行)
  - 详细中文注释解释金融逻辑
"""

import logging
from datetime import datetime, timezone

from app.schemas.strategy import (
    ActionType,
    ExecutionDetails,
    PositionSnapshot,
    TimingDecision,
)

logger = logging.getLogger("alphatheta.strategy.lifecycle")

# ── 策略参数 ──
TAKE_PROFIT_THRESHOLD = 0.50  # 止盈比例: 权利金回收 50%
GAMMA_TRAP_DTE = 21           # Gamma 警戒线: DTE ≤ 21 天
DEEP_ITM_THRESHOLD = 0.05     # 深度 ITM 阈值: 标的穿过行权价 > 5%


class LifecycleScannerEngine:
    """
    生命周期巡检引擎 — 系统的"持仓守卫"

    无状态设计: 每次调用 scan() 都是独立的巡检过程
    输入: 所有存量持仓的快照列表
    输出: 需要执行的操作信号列表
    """

    def scan(self, positions: list[PositionSnapshot]) -> list[TimingDecision]:
        """
        巡检所有存量持仓, 生成操作信号列表

        只扫描期权空头 (Short Put / Short Call):
        - Long Stock 不需要止盈/展期 (由开仓引擎管理)
        - Short Option 才有权利金衰减、Gamma 风险等问题

        返回的信号列表可能包含来自不同规则的决策,
        OMS 应按 confidence 降序排列执行
        """
        now = datetime.now(timezone.utc)
        signals: list[TimingDecision] = []

        for pos in positions:
            # 只巡检期权空头
            if pos.position_type not in ("short_put", "short_call"):
                continue

            # Rule 1: 止盈检查
            tp_signal = self._check_take_profit(pos, now)
            if tp_signal is not None:
                signals.append(tp_signal)
                # 止盈优先级最高 → 跳过后续规则 (同一持仓不重复出信号)
                continue

            # Rule 2: Gamma Trap 检查
            gamma_signal = self._check_gamma_trap(pos, now)
            if gamma_signal is not None:
                signals.append(gamma_signal)
                continue

            # Rule 3: 深度 ITM 检查
            itm_signal = self._check_deep_itm(pos, now)
            if itm_signal is not None:
                signals.append(itm_signal)

        logger.info(
            f"🔍 Lifecycle scan: {len(positions)} positions → {len(signals)} signals"
        )
        return signals

    # ══════════════════════════════════════════════════════════════
    # Rule 1: Take-Profit (50% 动态止盈)
    # ══════════════════════════════════════════════════════════════

    def _check_take_profit(
        self, pos: PositionSnapshot, now: datetime
    ) -> TimingDecision | None:
        """
        50% 止盈规则

        原理:
        期权卖方的利润来源是时间价值 (Theta) 的自然衰减。
        这个衰减不是线性的, 而是一条"后期加速"曲线:
          ┌──────────────────────────────┐
          │ 收取的权利金                  │
          │ ████████████████████████████  │ ← 100%
          │ ████████████████░░░░░░░░░░░  │ ← ~50% (大约在 DTE 的一半时达到)
          │ ████████░░░░░░░░░░░░░░░░░░░  │ ← ~70%
          │ ██░░░░░░░░░░░░░░░░░░░░░░░░░  │ ← ~90%
          │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ ← 到期 (100%)
          └──────────────────────────────┘

        前 50% 利润可能只需要总时间的 30%;
        后 50% 利润需要剩余的 70% 时间, 而且面临方向风险。
        因此在 50% 时平仓, 释放保证金, 重新卖出新合约
        = "快速周转" 策略, 提高年化收益率。
        """
        if pos.profit_pct < TAKE_PROFIT_THRESHOLD:
            return None

        logger.info(
            f"💰 Take-Profit: {pos.ticker} {pos.contract_symbol} "
            f"profit={pos.profit_pct:.1%} ≥ {TAKE_PROFIT_THRESHOLD:.0%}"
        )

        return TimingDecision(
            action_type=ActionType.BUY_TO_CLOSE,
            target_ticker=pos.ticker,
            scene_label=f"Take-Profit: {pos.profit_pct:.0%} Reached",
            confidence=0.85,
            execution_details=ExecutionDetails(
                contract_symbol=pos.contract_symbol,
                strike_price=pos.strike,
                dte=pos.dte,
                # 买回成本 = 当前 ask 价 (current_cost)
                limit_price=round(pos.current_cost, 2),
                expiration=pos.expiration,
            ),
            reasoning=(
                f"{pos.ticker} {pos.position_type} "
                f"初始权利金=${pos.initial_premium:.2f}, "
                f"当前买回成本=${pos.current_cost:.2f}, "
                f"浮盈比例={pos.profit_pct:.1%}。"
                f"已达到 50% 止盈线, 建议平仓落袋为安, "
                f"释放保证金后可立即重新开仓。"
            ),
            timestamp=now,
        )

    # ══════════════════════════════════════════════════════════════
    # Rule 2: Gamma Trap Avoidance (DTE ≤ 21 展期防御)
    # ══════════════════════════════════════════════════════════════

    def _check_gamma_trap(
        self, pos: PositionSnapshot, now: datetime
    ) -> TimingDecision | None:
        """
        Gamma Trap 防御规则

        什么是 Gamma 爆炸？
        ─────────────────
        Gamma 衡量的是 Delta 的变化速度。
        当 DTE < 21 天时, ATM 附近合约的 Gamma 值会急剧上升:

          Gamma
            ▲
            │         ╱╲  ← DTE=5 (Gamma 极高)
            │       ╱    ╲
            │     ╱   ╱╲  ╲  ← DTE=15
            │   ╱   ╱    ╲  ╲
            │ ╱   ╱        ╲  ╲  ← DTE=30
            │╱  ╱            ╲  ╲
            └──────────────────────→ 标的价格 (Strike 在中心)

        DTE < 21 + ATM/浮亏 = 极度危险区域:
        - 标的价格微小波动 → Delta 剧变 → 期权价格剧烈波动
        - 如果此时正好 ATM 或浮亏, 被行权风险骤增
        - 止损代价高昂 (Gamma 放大了损失)

        正确应对: ROLL OUT (展期)
        - 平掉近月合约 (平仓止血)
        - 卖出远月同 Strike 或更低 Strike 合约 (重新获得 Theta 保护)
        - 远月 Gamma 低 → 价格波动可控
        """
        # 条件: DTE ≤ 21 且 (浮亏 或 ATM 逼近)
        if pos.dte > GAMMA_TRAP_DTE:
            return None

        is_losing = pos.profit_pct < 0
        is_atm = pos.is_atm

        if not (is_losing or is_atm):
            return None

        trigger_reason = []
        if is_losing:
            trigger_reason.append(f"浮亏 {abs(pos.profit_pct):.1%}")
        if is_atm:
            trigger_reason.append(
                f"标的 ${pos.underlying_price:.2f} 逼近行权价 ${pos.strike:.2f}"
            )

        logger.warning(
            f"⚠️ Gamma Trap: {pos.ticker} {pos.contract_symbol} "
            f"DTE={pos.dte} {'|'.join(trigger_reason)}"
        )

        return TimingDecision(
            action_type=ActionType.ROLL_OUT,
            target_ticker=pos.ticker,
            scene_label=f"Gamma Trap: DTE={pos.dte} ≤ {GAMMA_TRAP_DTE}",
            confidence=0.80,
            execution_details=ExecutionDetails(
                contract_symbol=pos.contract_symbol,
                strike_price=pos.strike,
                dte=pos.dte,
                limit_price=round(pos.current_cost, 2),
                expiration=pos.expiration,
            ),
            reasoning=(
                f"{pos.ticker} {pos.position_type} DTE={pos.dte}天, "
                f"{'、'.join(trigger_reason)}。"
                f"进入 Gamma 爆炸区域, Gamma 值急剧上升, "
                f"标的价格微小波动将导致期权价格剧烈变化。"
                f"建议展期 (Roll Out) 至下月, 重新获得 Theta 时间价值保护。"
            ),
            timestamp=now,
        )

    # ══════════════════════════════════════════════════════════════
    # Rule 3: Deep ITM Alert (深度实值预警)
    # ══════════════════════════════════════════════════════════════

    def _check_deep_itm(
        self, pos: PositionSnapshot, now: datetime
    ) -> TimingDecision | None:
        """
        深度 ITM 预警规则

        什么是 Assignment (被指派) 风险？
        ──────────────────────────────
        当 Short Option 处于深度 ITM 时:
        - Short Put: 标的暴跌, 价格远低于行权价 → 对手方会提前行权, 你必须以行权价买入
        - Short Call: 标的暴涨, 价格远高于行权价 → 对手方会提前行权, 你必须以行权价卖出

        深度 ITM (标的穿过行权价 > 5%) 几乎 100% 会被行权。
        如果不想被现金交割, 必须提前平仓或展期。
        """
        if not pos.strike or not pos.is_in_the_money:
            return None

        # 计算穿越深度
        if "put" in pos.position_type:
            depth_pct = (pos.strike - pos.underlying_price) / pos.strike
        else:  # call
            depth_pct = (pos.underlying_price - pos.strike) / pos.strike

        if depth_pct < DEEP_ITM_THRESHOLD:
            return None

        logger.warning(
            f"🔴 Deep ITM: {pos.ticker} {pos.contract_symbol} "
            f"depth={depth_pct:.1%} > {DEEP_ITM_THRESHOLD:.0%}"
        )

        return TimingDecision(
            action_type=ActionType.ROLL_OUT,
            target_ticker=pos.ticker,
            scene_label=f"Deep ITM: {depth_pct:.1%} Through Strike",
            confidence=0.75,
            execution_details=ExecutionDetails(
                contract_symbol=pos.contract_symbol,
                strike_price=pos.strike,
                dte=pos.dte,
                limit_price=round(pos.current_cost, 2),
                expiration=pos.expiration,
            ),
            reasoning=(
                f"{pos.ticker} {pos.position_type} 已深度实值, "
                f"标的 ${pos.underlying_price:.2f} 穿过行权价 ${pos.strike:.2f} "
                f"幅度 {depth_pct:.1%}。"
                f"被行权 (Assignment) 风险极高。"
                f"建议立即展期至下月更低行权价, 或平仓止损。"
            ),
            timestamp=now,
        )


# ── 模块级便捷函数 ──

def scan_portfolio_lifecycle(
    positions: list[PositionSnapshot],
) -> list[TimingDecision]:
    """
    生命周期巡检的便捷入口

    用法:
        from app.services.strategy_lifecycle import scan_portfolio_lifecycle
        signals = scan_portfolio_lifecycle(position_snapshots)
    """
    engine = LifecycleScannerEngine()
    return engine.scan(positions)
