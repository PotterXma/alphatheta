"""
开仓决策大脑 (Entry Decision Tree)

职责: 基于大盘指标 (VIX, RSI) + 期权链筛选, 生成建仓信号

决策树流程 (短路评估, 按优先级从高到低):
┌─────────────────────────────────────────────────────────┐
│ Priority 0: VIX > 35 → HOLD (系统性风险, 不进场)        │
│ Priority 1: 财报 < 3 天 → HOLD (规避 IV Crush)          │
│ Scene A:    RSI < 40 且无持仓 → SELL_PUT (超卖抄底)     │
│ Scene B:    RSI > 60 且有持仓 → SELL_CALL (超买备兑)    │
│ Scene C:    RSI > 60 且无持仓 → HOLD (拒绝追高)         │
│ Scene D:    RSI 40-60 且无持仓 → BUY_WRITE (震荡建仓)   │
│ Fallback:   → HOLD                                      │
└─────────────────────────────────────────────────────────┘

期权链寻优:
  1. Delta-Driven: 寻找 |Delta| 最接近 0.16 的合约 (84% 胜率)
  2. Liquidity:    OI > 500 且 Volume > 50 (过滤流动性陷阱)
  3. Spread:       Bid/Ask 价差 < 8% (过滤宽幅价差)

设计原则:
  - 纯函数, 无 I/O 依赖 — 可单元测试
  - 所有金额用 round() 控制精度
  - 详细中文注释解释金融逻辑
"""

import logging
from datetime import date, datetime, timezone

from app.schemas.strategy import (
    ActionType,
    ExecutionDetails,
    OptionContract,
    StrategyMarketContext,
    TimingDecision,
)

logger = logging.getLogger("alphatheta.strategy.entry")

# ── 策略参数 (可后续迁移到 config) ──
TARGET_DELTA = 0.16       # 目标 Delta: 0.16 ≈ 84% 胜率 (1σ 标准差)
MIN_OPEN_INTEREST = 500   # 最低未平仓合约数 (低于此值视为流动性不足)
MIN_VOLUME = 50           # 最低日成交量 (低于此值无法保证成交)
MAX_SPREAD_PCT = 8.0      # 最大 Bid/Ask 价差百分比 (超过此值成交成本过高)
VIX_CIRCUIT_BREAKER = 35  # VIX 熔断阈值 (超过此值市场处于极度恐慌)
EARNINGS_BLACKOUT_DAYS = 3  # 财报黑名单天数 (距离财报 < 3 天则不进场)


class StrategyEntryEngine:
    """
    开仓决策引擎 — 系统的"开仓大脑"

    无状态设计: 每次调用 evaluate() 都是独立的决策过程
    所有依赖通过 StrategyMarketContext DTO 传入, 不直接访问 DB/API
    """

    def evaluate(self, ctx: StrategyMarketContext) -> TimingDecision:
        """
        评估市场状态, 生成择时决策

        短路评估 (Short-Circuit Evaluation):
        优先级高的规则命中后, 后续规则不再执行
        这确保了系统在高风险场景下绝对不会误操作
        """
        now = datetime.now(timezone.utc)

        # ════════════════════════════════════════
        # Priority 0: VIX 熔断保护
        # ════════════════════════════════════════
        # VIX > 35 意味着市场处于极度恐慌状态 (如 2020 年 3 月、2008 年金融危机)
        # 此时期权 IV 极高, 卖出期权看似权利金丰厚但方向风险巨大
        # 正确做法: 等待 VIX 回落到 25 以下再考虑入场
        if ctx.vix > VIX_CIRCUIT_BREAKER:
            logger.warning(f"🚨 VIX Override: {ctx.vix:.1f} > {VIX_CIRCUIT_BREAKER} — HOLD")
            return TimingDecision(
                action_type=ActionType.HOLD,
                target_ticker=ctx.ticker,
                scene_label="Priority 0: VIX Circuit Breaker",
                confidence=0.95,
                reasoning=(
                    f"VIX={ctx.vix:.1f} 超过熔断阈值 {VIX_CIRCUIT_BREAKER}。"
                    f"市场处于极度恐慌, 期权 IV 膨胀, 方向判断难度极高。"
                    f"等待 VIX 回落至 25 以下再考虑进场。"
                ),
                timestamp=now,
            )

        # ════════════════════════════════════════
        # Priority 1: 财报日黑名单
        # ════════════════════════════════════════
        # 财报发布前后, 期权会出现 "IV Crush" 现象:
        # - 财报前: 市场不确定性高 → IV 升高 → 期权价格虚高
        # - 财报后: 不确定性消除 → IV 骤降 → 即使方向对了, 权利金也大幅缩水
        # - 如果方向判断错误 + IV Crush → 双重打击
        # 因此在财报前 3 天内不新建仓位
        if ctx.earnings_date is not None:
            days_to_earnings = (ctx.earnings_date - date.today()).days
            if 0 <= days_to_earnings < EARNINGS_BLACKOUT_DAYS:
                logger.info(
                    f"📅 Earnings Blackout: {ctx.ticker} reports in {days_to_earnings}d — HOLD"
                )
                return TimingDecision(
                    action_type=ActionType.HOLD,
                    target_ticker=ctx.ticker,
                    scene_label="Priority 1: Earnings Blackout",
                    confidence=0.90,
                    reasoning=(
                        f"{ctx.ticker} 将在 {days_to_earnings} 天后发布财报。"
                        f"财报期间 IV Crush 风险极高, 暂停新建仓位。"
                    ),
                    timestamp=now,
                )

        # ════════════════════════════════════════
        # Scene A: 超卖抄底 (RSI < 40, 无持仓)
        # ════════════════════════════════════════
        # RSI < 40 意味着标的被超卖, 短期内大概率反弹
        # 适合卖出看跌期权 (Sell Put):
        # - 如果标的继续下跌并触及行权价 → 以折扣价接盘正股 (正是我们想要的)
        # - 如果标的反弹 → 权利金纯收益, 合约到期变废纸
        # 但必须是"无持仓"状态, 避免过度集中
        if ctx.rsi_14 < 40 and not ctx.has_position:
            return self._build_option_decision(
                ctx=ctx,
                action_type=ActionType.SELL_PUT,
                option_type="put",
                scene_label="Scene A: Oversold (RSI < 40)",
                confidence=0.75,
                reasoning=(
                    f"RSI={ctx.rsi_14:.1f} < 40, 标的超卖, VIX={ctx.vix:.1f} 可控。"
                    f"卖出看跌期权, 目标 Delta={TARGET_DELTA} (约 {int((1-TARGET_DELTA)*100)}% 胜率)。"
                    f"若被行权则以折扣价接盘 {ctx.ticker}。"
                ),
                now=now,
            )

        # ════════════════════════════════════════
        # Scene B: 超买备兑 (RSI > 60, 有持仓)
        # ════════════════════════════════════════
        # RSI > 60 意味着标的可能短期见顶
        # 已持有正股 → 卖出看涨期权 (Covered Call / 备兑开仓):
        # - 标的继续涨 → 以行权价卖出正股 (利润有上限但稳赚)
        # - 标的横盘或下跌 → 权利金纯收益, 降低持仓成本
        if ctx.rsi_14 > 60 and ctx.has_position:
            return self._build_option_decision(
                ctx=ctx,
                action_type=ActionType.SELL_CALL,
                option_type="call",
                scene_label="Scene B: Overbought + Position (RSI > 60)",
                confidence=0.70,
                reasoning=(
                    f"RSI={ctx.rsi_14:.1f} > 60, 标的偏高, 已持有正股。"
                    f"卖出备兑看涨期权锁定利润, 降低持仓成本。"
                ),
                now=now,
            )

        # ════════════════════════════════════════
        # Scene C: 拒绝追高 (RSI > 60, 无持仓)
        # ════════════════════════════════════════
        # RSI > 60 但没有持仓 → 此时买入正股风险高 (追高)
        # 也不适合卖 Put (下方空间大, 可能被套)
        # 正确做法: 观望等待回调
        if ctx.rsi_14 > 60 and not ctx.has_position:
            return TimingDecision(
                action_type=ActionType.HOLD,
                target_ticker=ctx.ticker,
                scene_label="Scene C: Overbought Without Position",
                confidence=0.65,
                reasoning=(
                    f"RSI={ctx.rsi_14:.1f} > 60, 但无持仓。"
                    f"此时追高买入风险大, 等待 RSI 回落至 50 以下再建仓。"
                ),
                timestamp=now,
            )

        # ════════════════════════════════════════
        # Scene D: 震荡建仓 (RSI 40-60, 无持仓)
        # ════════════════════════════════════════
        # RSI 在 40-60 之间 = 市场不温不火, 中性区间
        # 适合 Buy-Write 组合:
        # - 买入 100 股正股
        # - 同时卖出 1 张 OTM Call (备兑降低成本)
        # 这是最稳健的建仓方式, 相当于"边买边卖保险"
        if 40 <= ctx.rsi_14 <= 60 and not ctx.has_position:
            return self._build_option_decision(
                ctx=ctx,
                action_type=ActionType.BUY_WRITE,
                option_type="call",  # Buy-Write 中卖出的是 Call
                scene_label="Scene D: Range-Bound (RSI 40-60)",
                confidence=0.60,
                reasoning=(
                    f"RSI={ctx.rsi_14:.1f} 处于中性区间, 无持仓。"
                    f"执行 Buy-Write: 买入 100 股 {ctx.ticker} + 卖出 1 张 OTM Call。"
                    f"通过权利金降低建仓成本。"
                ),
                now=now,
            )

        # ════════════════════════════════════════
        # Fallback: 无匹配场景 → HOLD
        # ════════════════════════════════════════
        return TimingDecision(
            action_type=ActionType.HOLD,
            target_ticker=ctx.ticker,
            scene_label="Fallback: No Matching Scene",
            confidence=0.30,
            reasoning=(
                f"RSI={ctx.rsi_14:.1f}, VIX={ctx.vix:.1f}, "
                f"has_position={ctx.has_position}. 无匹配决策场景。"
            ),
            timestamp=now,
        )

    # ══════════════════════════════════════════════════════════════
    # Private — 期权链寻优
    # ══════════════════════════════════════════════════════════════

    def _build_option_decision(
        self,
        ctx: StrategyMarketContext,
        action_type: ActionType,
        option_type: str,
        scene_label: str,
        confidence: float,
        reasoning: str,
        now: datetime,
    ) -> TimingDecision:
        """
        构建期权交易决策 — 包含 Delta 寻优 + 流动性过滤

        如果找不到满足条件的合约, 降级为 HOLD
        """
        # 从期权链中筛选目标类型的合约 (put 或 call)
        candidates = [
            c for c in ctx.options_chain
            if c.option_type == option_type
        ]

        if not candidates:
            logger.info(f"📋 No {option_type} contracts in chain for {ctx.ticker}")
            return TimingDecision(
                action_type=ActionType.HOLD,
                target_ticker=ctx.ticker,
                scene_label=f"{scene_label} → No Contracts",
                confidence=0.20,
                reasoning=f"{reasoning}\n⚠ 期权链中无可用的 {option_type} 合约。",
                timestamp=now,
            )

        # Step 1: Delta 寻优
        optimal = self._find_optimal_strike(candidates, TARGET_DELTA)
        if optimal is None:
            return TimingDecision(
                action_type=ActionType.HOLD,
                target_ticker=ctx.ticker,
                scene_label=f"{scene_label} → No Liquid Contract",
                confidence=0.20,
                reasoning=f"{reasoning}\n⚠ 无满足流动性条件的合约。",
                timestamp=now,
            )

        # 构建执行细节
        exec_details = ExecutionDetails(
            contract_symbol=optimal.symbol,
            strike_price=optimal.strike,
            target_delta=TARGET_DELTA,
            actual_delta=optimal.delta,
            dte=self._calc_dte(optimal.expiration),
            limit_price=optimal.mid_price,
            expiration=optimal.expiration,
            estimated_premium=optimal.mid_price,
            open_interest=optimal.open_interest,
            volume=optimal.volume,
        )

        logger.info(
            f"✅ {scene_label}: {action_type.value} {optimal.symbol} "
            f"Δ={optimal.delta:.3f} strike=${optimal.strike:.2f} "
            f"mid=${optimal.mid_price:.2f} OI={optimal.open_interest}"
        )

        return TimingDecision(
            action_type=action_type,
            target_ticker=ctx.ticker,
            scene_label=scene_label,
            confidence=confidence,
            execution_details=exec_details,
            reasoning=reasoning,
            timestamp=now,
        )

    def _find_optimal_strike(
        self,
        chain: list[OptionContract],
        target_delta: float = TARGET_DELTA,
    ) -> OptionContract | None:
        """
        Delta-Driven 期权合约寻优

        算法:
        1. 按 |actual_delta - target_delta| 升序排序 (Delta 最接近目标的优先)
        2. 逐一检查流动性条件:
           - OI > 500 (确保有足够的对手方)
           - Volume > 50 (确保当日有成交)
           - Bid/Ask Spread < 8% (确保成交成本可控)
        3. 返回第一个满足所有条件的合约
        4. 如果没有满足条件的 → 返回 None (降级为 HOLD)

        为什么选 Delta=0.16？
        ──────────────────────
        根据正态分布, |Delta| ≈ 0.16 意味着:
        - 该合约处于约 1 个标准差 OTM (Out-of-The-Money)
        - 到期时被行权的概率约 16%
        - 换言之, 约 84% 的概率合约到期变废纸, 权利金全部到手
        - 这是期权卖方最经典的"甜蜜点" — 胜率高且权利金不算太低
        """
        # 按 Delta 接近程度排序
        sorted_chain = sorted(
            chain,
            key=lambda c: abs(abs(c.delta) - target_delta),
        )

        for contract in sorted_chain:
            # 流动性三重过滤
            if contract.open_interest < MIN_OPEN_INTEREST:
                logger.debug(
                    f"  ✖ {contract.symbol}: OI={contract.open_interest} < {MIN_OPEN_INTEREST}"
                )
                continue

            if contract.volume < MIN_VOLUME:
                logger.debug(
                    f"  ✖ {contract.symbol}: Vol={contract.volume} < {MIN_VOLUME}"
                )
                continue

            if contract.spread_pct > MAX_SPREAD_PCT:
                logger.debug(
                    f"  ✖ {contract.symbol}: Spread={contract.spread_pct:.1f}% > {MAX_SPREAD_PCT}%"
                )
                continue

            # 通过所有过滤 → 选中
            return contract

        logger.info("  ✖ No contract passed liquidity filters")
        return None

    @staticmethod
    def _calc_dte(expiration: str) -> int:
        """计算剩余到期天数"""
        exp = datetime.strptime(expiration, "%Y-%m-%d").date()
        return max(0, (exp - date.today()).days)


# ── 模块级便捷函数 (供路由层直接调用) ──

def evaluate_market_entry(ctx: StrategyMarketContext) -> TimingDecision:
    """
    开仓决策的便捷入口

    用法:
        from app.services.strategy_entry import evaluate_market_entry
        decision = evaluate_market_entry(market_context)
    """
    engine = StrategyEntryEngine()
    return engine.evaluate(ctx)
