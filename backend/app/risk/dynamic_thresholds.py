"""
动态风控参数计算引擎 — ATR / IV 自适应防线

核心金融数学:

1. Implied Move (隐含移动):
   IM = Price × IV × √(DTE / 365)
   含义: 市场共识价格在到期日的 1 标准差移动幅度
   例: SPY $685, IV=20%, DTE=30 → IM = 685 × 0.20 × √(30/365) = $39.26
   1σ 区间: $645.74 ~ $724.26

2. ATR-14 (14日真实波动幅度):
   ATR = SMA(14, max(High-Low, |High-PrevClose|, |Low-PrevClose|))
   含义: 过去14个交易日的平均日内波动幅度
   用途: 2×ATR 作为短期极值防线 (约覆盖 95% 的日内波动)

3. 策略特化逻辑:
   - Buy-Write: 不能用传统止损! 期权浮亏 = 正股浮盈的对冲
     上涨: 关注时间价值枯竭 → Roll Up & Out
     下跌: 2×ATR 硬止损 → 组合平仓
   - Sell Put: 关注被指派成本 vs 当前价
   - Naked: 传统止损止盈
"""

import logging
import math
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger("alphatheta.risk.dynamic")


class RiskTagType(StrEnum):
    """风控级别 — 映射前端颜色"""
    DANGER = "danger"       # 红色: 尾部风险, 立即行动
    WARNING = "warning"     # 橙色: 接近防线, 准备行动
    INFO = "info"           # 青色: 常规监控
    SUCCESS = "success"     # 绿色: 安全区间


class StrategyType(StrEnum):
    """策略类型"""
    BUY_WRITE = "buy_write"
    SELL_PUT = "sell_put"
    NAKED_LONG = "naked_long"
    COVERED_CALL = "covered_call"


@dataclass
class RiskScenario:
    """
    单条风控情景 — 前端渲染的最小单元

    前端根据 tag_type 渲染不同颜色的微光边框:
      danger  → 红色脉冲边框
      warning → 橙色渐变边框
      info    → 青色常规边框
      success → 绿色安静边框
    """
    scenario_name: str          # 情景名称 (如 "2σ 下跌防线")
    trigger_condition: str      # 触发条件文本
    action_plan: str            # 应对动作
    tag_type: str               # danger / warning / info / success
    threshold_price: float | None = None  # 触发价格锚点
    priority: int = 5           # 优先级 (1=最高)


@dataclass
class DynamicRiskParams:
    """动态风控参数集合"""
    ticker: str
    strategy_type: str
    current_price: float
    implied_move_1sigma: float       # 1σ 隐含移动
    implied_move_2sigma: float       # 2σ 隐含移动
    atr_stop_loss: float             # 2×ATR 止损线
    upside_1sigma: float             # 1σ 上行边界
    downside_1sigma: float           # 1σ 下行边界
    scenarios: list[RiskScenario] = field(default_factory=list)


def calculate_dynamic_risk_params(
    ticker: str,
    strategy_type: str,
    current_price: float,
    iv: float,
    atr_14: float,
    dte: int = 30,
    strike: float | None = None,
    premium: float | None = None,
    option_market_price: float | None = None,
) -> DynamicRiskParams:
    """
    计算动态风控参数 — 核心入口

    参数:
        ticker: 标的代码
        strategy_type: 策略类型 (buy_write, sell_put, etc.)
        current_price: 正股现价
        iv: 隐含波动率 (年化, 小数形式, 如 0.20 = 20%)
        atr_14: 14日真实波动幅度 (ATR)
        dte: 距到期日天数
        strike: 期权行权价 (策略需要时)
        premium: 期权权利金 (策略需要时)
        option_market_price: 期权当前市场价 (用于时间价值计算)

    返回:
        DynamicRiskParams — 包含所有动态防线和情景列表
    """
    # ── 基础数学 ──

    # Implied Move: Price × IV × √(DTE/365)
    # 1σ 覆盖 68.2% 的概率, 2σ 覆盖 95.4%
    sqrt_dte = math.sqrt(dte / 365.0) if dte > 0 else 0
    im_1sigma = current_price * iv * sqrt_dte
    im_2sigma = im_1sigma * 2

    # ATR 防线: 现价 - 2×ATR (短期极值防线)
    atr_stop = current_price - 2 * atr_14

    # 波动区间
    upside_1sigma = current_price + im_1sigma
    downside_1sigma = current_price - im_1sigma

    params = DynamicRiskParams(
        ticker=ticker,
        strategy_type=strategy_type,
        current_price=current_price,
        implied_move_1sigma=round(im_1sigma, 2),
        implied_move_2sigma=round(im_2sigma, 2),
        atr_stop_loss=round(atr_stop, 2),
        upside_1sigma=round(upside_1sigma, 2),
        downside_1sigma=round(downside_1sigma, 2),
    )

    # ── 策略特化情景 ──
    if strategy_type == StrategyType.BUY_WRITE:
        params.scenarios = _build_buy_write_scenarios(
            ticker, current_price, iv, atr_14, dte,
            im_1sigma, im_2sigma, atr_stop,
            strike=strike, premium=premium,
            option_market_price=option_market_price,
        )
    elif strategy_type == StrategyType.SELL_PUT:
        params.scenarios = _build_sell_put_scenarios(
            ticker, current_price, iv, atr_14, dte,
            im_1sigma, im_2sigma, atr_stop,
            strike=strike, premium=premium,
        )
    else:
        params.scenarios = _build_generic_scenarios(
            ticker, current_price, iv, atr_14, dte,
            im_1sigma, im_2sigma, atr_stop,
        )

    # 按优先级排序
    params.scenarios.sort(key=lambda s: s.priority)
    return params


# ══════════════════════════════════════════════════════════════════
# 策略特化: Buy-Write (备兑开仓)
# ══════════════════════════════════════════════════════════════════

def _build_buy_write_scenarios(
    ticker: str,
    price: float,
    iv: float,
    atr: float,
    dte: int,
    im1: float,
    im2: float,
    atr_stop: float,
    strike: float | None = None,
    premium: float | None = None,
    option_market_price: float | None = None,
) -> list[RiskScenario]:
    """
    Buy-Write 专用风控情景

    关键认知:
    - 期权浮亏 ≠ 风险! 正股上涨时 Short Call 浮亏, 但正股浮盈完美对冲
    - "止损"概念不适用于 Short Call 腿
    - 上涨风险: 时间价值枯竭 → 应 Roll Up & Out
    - 下跌风险: 正股硬止损 @  2×ATR
    """
    scenarios = []
    strike = strike or round(price * 1.02, 2)
    premium = premium or 5.0

    # ── 1. 上涨防守: Roll Up & Out (时间价值枯竭) ──
    # 当正股暴涨导致 Short Call 深度 ITM, 时间价值 → 0
    # 此时期权几乎是 Delta=1 的合成正股, 失去保护意义
    roll_trigger = strike + im1 * 0.5  # 超过行权价半个 sigma
    if option_market_price and strike:
        intrinsic = max(0, price - strike)
        extrinsic = max(0, option_market_price - intrinsic)
        if extrinsic < 0.10:
            scenarios.append(RiskScenario(
                scenario_name="🔄 时间价值枯竭 — Roll Up & Out",
                trigger_condition=(
                    f"Short Call 时间价值仅 ${extrinsic:.2f} (< $0.10)\n"
                    f"期权已深度 ITM, 失去保护意义"
                ),
                action_plan=(
                    f"买回当前 Call → 卖出 Strike ${strike + 5:.0f}, +30天 的 新Call\n"
                    f"目标: 释放上涨空间, 继续收取权利金"
                ),
                tag_type=RiskTagType.WARNING,
                threshold_price=round(roll_trigger, 2),
                priority=2,
            ))

    scenarios.append(RiskScenario(
        scenario_name="⬆️ 行权利润锁定区 (非风险)",
        trigger_condition=(
            f"正股涨超行权价 ${strike:.2f}\n"
            f"→ 正股被 Call 走, 获得最大利润"
        ),
        action_plan=(
            f"这不是风险! 被行权 = 计划内的利润终点\n"
            f"最大收益 = (${strike:.2f} - ${price:.2f} + ${premium:.2f}) × 100 "
            f"= ${(strike - price + premium) * 100:.2f}"
        ),
        tag_type=RiskTagType.SUCCESS,
        threshold_price=strike,
        priority=4,
    ))

    # ── 2. 隐含波动区间 (常规监控) ──
    scenarios.append(RiskScenario(
        scenario_name="📊 1σ 隐含波动区间",
        trigger_condition=(
            f"市场共识: {dte}天内 68.2% 概率在\n"
            f"${price - im1:.2f} ~ ${price + im1:.2f} 区间内"
        ),
        action_plan="常规监控, 无需操作",
        tag_type=RiskTagType.INFO,
        threshold_price=None,
        priority=5,
    ))

    # ── 3. 下跌防守: 2×ATR 硬止损 ──
    break_even = price - premium
    scenarios.append(RiskScenario(
        scenario_name="⚠️ 盈亏平衡防线",
        trigger_condition=(
            f"正股跌破 ${break_even:.2f} (现价 - 权利金)\n"
            f"→ 整体仓位开始进入浮亏"
        ),
        action_plan=(
            f"关注但不急于行动 — 权利金提供 ${premium:.2f}/股 安全垫\n"
            f"考虑: 若基本面未变, 可继续持有等回升"
        ),
        tag_type=RiskTagType.WARNING,
        threshold_price=round(break_even, 2),
        priority=3,
    ))

    scenarios.append(RiskScenario(
        scenario_name="🚨 2×ATR 尾部风险止损线",
        trigger_condition=(
            f"正股跌破 ${atr_stop:.2f} (现价 - 2×ATR ${atr * 2:.2f})\n"
            f"→ 超出正常波动范围, 可能趋势性下跌"
        ),
        action_plan=(
            f"立即执行组合平仓:\n"
            f"1. Buy to Close Short Call (锁定权利金利润)\n"
            f"2. 卖出正股止损\n"
            f"不要 Roll Down — 避免锁死亏损"
        ),
        tag_type=RiskTagType.DANGER,
        threshold_price=atr_stop,
        priority=1,
    ))

    # ── 4. 2σ 极端尾部 ──
    extreme_down = price - im2
    scenarios.append(RiskScenario(
        scenario_name="💀 2σ 极端黑天鹅防线",
        trigger_condition=(
            f"正股跌破 ${extreme_down:.2f} (2σ 隐含移动)\n"
            f"→ 发生概率 < 4.6%, 但一旦发生损失巨大"
        ),
        action_plan=(
            f"紧急对冲: 买入 Put 保护 (Protective Put)\n"
            f"或直接清仓所有相关头寸"
        ),
        tag_type=RiskTagType.DANGER,
        threshold_price=round(extreme_down, 2),
        priority=1,
    ))

    return scenarios


# ══════════════════════════════════════════════════════════════════
# 策略特化: Sell Put (卖出看跌)
# ══════════════════════════════════════════════════════════════════

def _build_sell_put_scenarios(
    ticker, price, iv, atr, dte, im1, im2, atr_stop,
    strike=None, premium=None,
) -> list[RiskScenario]:
    strike = strike or round(price * 0.95, 2)
    premium = premium or 3.0

    return [
        RiskScenario(
            scenario_name="✅ Put 到期作废 (最佳结果)",
            trigger_condition=f"到期日股价 > ${strike:.2f} → Put OTM",
            action_plan=f"净收入权利金 ${premium * 100:.2f}, 资金释放",
            tag_type=RiskTagType.SUCCESS,
            threshold_price=strike,
            priority=4,
        ),
        RiskScenario(
            scenario_name="⚠️ 接近行权价 (指派风险区)",
            trigger_condition=(
                f"股价接近 ${strike:.2f} (距离 < 1×ATR ${atr:.2f})\n"
                f"→ 可能被指派买入 100 股"
            ),
            action_plan=(
                f"评估: 是否愿意以 ${strike - premium:.2f} 持有该标的?\n"
                f"若否 → Roll Down & Out 推迟到更低 Strike"
            ),
            tag_type=RiskTagType.WARNING,
            threshold_price=round(strike + atr, 2),
            priority=3,
        ),
        RiskScenario(
            scenario_name="🚨 2×ATR 深度 ITM — 尾部风险",
            trigger_condition=(
                f"股价跌破 ${atr_stop:.2f} (2×ATR 防线)\n"
                f"→ Put 深度 ITM, 被指派后即大幅浮亏"
            ),
            action_plan=(
                f"Buy to Close 平仓止损\n"
                f"不要等被指派 — 主动平仓损失更可控"
            ),
            tag_type=RiskTagType.DANGER,
            threshold_price=atr_stop,
            priority=1,
        ),
        RiskScenario(
            scenario_name="📊 1σ 隐含波动区间",
            trigger_condition=f"68.2% 概率区间: ${price - im1:.2f} ~ ${price + im1:.2f}",
            action_plan="常规监控",
            tag_type=RiskTagType.INFO,
            priority=5,
        ),
    ]


# ══════════════════════════════════════════════════════════════════
# 通用策略 (裸持/默认)
# ══════════════════════════════════════════════════════════════════

def _build_generic_scenarios(
    ticker, price, iv, atr, dte, im1, im2, atr_stop,
) -> list[RiskScenario]:
    return [
        RiskScenario(
            scenario_name="📊 1σ 隐含波动区间",
            trigger_condition=f"68.2% 概率: ${price - im1:.2f} ~ ${price + im1:.2f}",
            action_plan="常规监控区间",
            tag_type=RiskTagType.INFO,
            priority=5,
        ),
        RiskScenario(
            scenario_name="⚠️ 1σ 下行边界",
            trigger_condition=f"跌破 ${price - im1:.2f} (1σ 隐含移动)",
            action_plan="减仓 25% 或加入止损单",
            tag_type=RiskTagType.WARNING,
            threshold_price=round(price - im1, 2),
            priority=3,
        ),
        RiskScenario(
            scenario_name="🚨 2×ATR 止损线",
            trigger_condition=f"跌破 ${atr_stop:.2f} (2×ATR 防线)",
            action_plan="立即止损清仓",
            tag_type=RiskTagType.DANGER,
            threshold_price=atr_stop,
            priority=1,
        ),
        RiskScenario(
            scenario_name="💀 2σ 极端防线",
            trigger_condition=f"跌破 ${price - im2:.2f} (2σ 尾部)",
            action_plan="紧急对冲或全清",
            tag_type=RiskTagType.DANGER,
            threshold_price=round(price - im2, 2),
            priority=1,
        ),
    ]
