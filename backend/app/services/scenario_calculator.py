"""
期权盈亏推演引擎 (Scenario Calculator) — 纯数学, 零副作用

以 Buy-Write (备兑开仓) 为基准策略:
  动作: 买入 100 股正股 + 卖出 1 张 OTM Call

盈亏公式:
  Break-even       = Stock Price - Premium
  Max Profit       = (Strike - Stock Price + Premium) * 100
  Max Loss         = (Stock Price - Premium) * 100  (正股归零, 但扣除权利金)
  Annualized ROI   = (Max Profit / Net Investment) * (365 / DTE)

场景推演:
  ⬆ 上涨至 Strike 以上 → 正股被行权, 获得 Max Profit (含权利金)
  ↔ 横盘 (Break-even ~ Strike) → 保留正股 + 全部权利金收入
  ⬇ 下跌至 Break-even 以下 → 开始产生浮亏, 但成本已降低 Premium
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("alphatheta.scenario")


@dataclass
class ScenarioResult:
    """单个情景推演结果"""
    label: str               # 情景标签 (Up / Down / Sideways)
    icon: str                # 图标 (⬆️ / ⬇️ / ↔️)
    description: str         # 情景描述
    pnl: float               # 绝对盈亏 (美元)
    pnl_pct: float           # 收益率 (%)
    color: str = "neutral"   # 颜色标识: green / red / neutral


@dataclass
class ScenarioAnalysis:
    """完整的情景推演分析"""
    strategy: str                                   # 策略类型 (Buy-Write, Sell Put, etc.)
    break_even: float                               # 盈亏平衡点
    max_profit: float                               # 最大潜在收益
    max_loss: float                                 # 最大潜在亏损
    net_investment: float                           # 净投入成本
    annualized_roi: float                           # 静态年化收益率
    scenarios: list[ScenarioResult] = field(default_factory=list)
    summary: str = ""                               # 一句话总结


def calculate_buy_write_scenario(
    stock_price: float,
    strike: float,
    premium: float,
    dte: int = 30,
) -> ScenarioAnalysis:
    """
    Buy-Write (备兑开仓) 盈亏推演

    参数:
        stock_price: 正股现价
        strike: 卖出 Call 的行权价
        premium: 卖出 Call 收到的权利金 (每股)
        dte: 距到期日天数

    数学推导 (per share basis, 乘以 100 = per contract):
        Net Cost     = stock_price - premium
        Break-even   = stock_price - premium
        Max Profit   = (strike - stock_price + premium) * 100
        Max Loss     = (stock_price - premium) * 100  (理论上股票跌到 0)
        ROI          = max_profit / net_cost_total
        Annual ROI   = ROI * (365 / dte)
    """
    # ── 核心计算 (per share) ──
    net_cost_per_share = stock_price - premium
    break_even = net_cost_per_share
    max_profit_per_share = strike - stock_price + premium
    max_loss_per_share = net_cost_per_share  # 股票跌到 0 的理论最大亏损

    # ── 每手合约 (100 股) ──
    net_investment = net_cost_per_share * 100
    max_profit = max_profit_per_share * 100
    max_loss = max_loss_per_share * 100  # 负值表示亏损

    # ── 收益率 ──
    roi_pct = (max_profit_per_share / net_cost_per_share * 100) if net_cost_per_share > 0 else 0
    annualized_roi = (roi_pct * 365 / dte) if dte > 0 else 0

    # ── 情景构建 ──
    scenarios = [
        # ⬆ 上涨情景: 股价 > Strike → 被行权
        ScenarioResult(
            label="上涨至行权价以上",
            icon="⬆️",
            description=(
                f"到期日股价 ≥ ${strike:.2f} → 正股被行权收走。\n"
                f"→ 卖出正股获得 ${strike:.2f}/股\n"
                f"→ 加上已收权利金 ${premium:.2f}/股\n"
                f"→ 最大绝对收益: ${max_profit:.2f}\n"
                f"→ 静态年化收益率: {annualized_roi:.1f}%"
            ),
            pnl=max_profit,
            pnl_pct=roi_pct,
            color="green",
        ),

        # ↔ 横盘情景: Break-even < 股价 < Strike → 保留正股 + 权利金
        ScenarioResult(
            label="横盘 (Break-even ~ Strike)",
            icon="↔️",
            description=(
                f"到期日股价在 ${break_even:.2f} ~ ${strike:.2f} 之间。\n"
                f"→ Call 到期作废OTM, 保留全部权利金 ${premium * 100:.2f}\n"
                f"→ 继续持有正股, 可再次卖出 Call\n"
                f"→ 实际持仓成本已从 ${stock_price:.2f} 降至 ${net_cost_per_share:.2f}"
            ),
            pnl=premium * 100,
            pnl_pct=(premium / net_cost_per_share * 100) if net_cost_per_share > 0 else 0,
            color="green",
        ),

        # ⬇ 下跌情景: 股价 < Break-even → 进入浮亏区域
        ScenarioResult(
            label="下跌 / 暴跌",
            icon="⬇️",
            description=(
                f"盈亏平衡点: ${break_even:.2f}\n"
                f"→ 权利金 ${premium * 100:.2f} 提供 ${premium:.2f}/股 的安全垫\n"
                f"→ 只要股价不跌破 ${break_even:.2f}, 整体仓位不亏损\n"
                f"→ 若继续暴跌, 承受与持有正股相同的浮亏风险\n"
                f"→ 但成本已降低 ${premium:.2f}/股 (优于裸持)"
            ),
            pnl=-max_loss,
            pnl_pct=-100.0,
            color="red",
        ),
    ]

    return ScenarioAnalysis(
        strategy="Buy-Write (备兑开仓)",
        break_even=round(break_even, 2),
        max_profit=round(max_profit, 2),
        max_loss=round(max_loss, 2),
        net_investment=round(net_investment, 2),
        annualized_roi=round(annualized_roi, 1),
        scenarios=scenarios,
        summary=(
            f"Buy-Write: 买入 100 股 @ ${stock_price:.2f}, "
            f"卖出 Call @ ${strike:.2f} 收权利金 ${premium:.2f}/股。"
            f"盈亏平衡 ${break_even:.2f}, "
            f"最大收益 ${max_profit:.2f} ({annualized_roi:.1f}% 年化)"
        ),
    )


def calculate_sell_put_scenario(
    stock_price: float,
    strike: float,
    premium: float,
    dte: int = 30,
) -> ScenarioAnalysis:
    """
    Sell Put (卖出看跌期权) 盈亏推演

    数学推导:
        Break-even   = strike - premium
        Max Profit   = premium * 100  (期权到期作废)
        Max Loss     = (strike - premium) * 100  (被指派买入, 股票跌到 0)
    """
    break_even = strike - premium
    max_profit = premium * 100
    max_loss = (strike - premium) * 100
    net_investment = strike * 100  # 保证金占用 (简化)

    roi_pct = (premium / strike * 100) if strike > 0 else 0
    annualized_roi = (roi_pct * 365 / dte) if dte > 0 else 0

    scenarios = [
        ScenarioResult(
            label="股价维持在行权价上方",
            icon="⬆️",
            description=(
                f"到期日股价 > ${strike:.2f} → Put 到期作废 OTM。\n"
                f"→ 净收入权利金 ${max_profit:.2f}\n"
                f"→ 年化收益率: {annualized_roi:.1f}%\n"
                f"→ 无需买入正股, 资金释放"
            ),
            pnl=max_profit,
            pnl_pct=roi_pct,
            color="green",
        ),
        ScenarioResult(
            label="股价跌破行权价 (被指派)",
            icon="⬇️",
            description=(
                f"到期日股价 < ${strike:.2f} → 被指派以 ${strike:.2f} 买入 100 股。\n"
                f"→ 盈亏平衡: ${break_even:.2f} (含权利金抵扣)\n"
                f"→ 实际买入成本 = ${break_even:.2f}/股\n"
                f"→ 若跌破此价, 开始浮亏"
            ),
            pnl=-max_loss,
            pnl_pct=-100.0,
            color="red",
        ),
    ]

    return ScenarioAnalysis(
        strategy="Sell Put (卖出看跌)",
        break_even=round(break_even, 2),
        max_profit=round(max_profit, 2),
        max_loss=round(max_loss, 2),
        net_investment=round(net_investment, 2),
        annualized_roi=round(annualized_roi, 1),
        scenarios=scenarios,
        summary=(
            f"Sell Put @ ${strike:.2f}, 权利金 ${premium:.2f}/股。"
            f"盈亏平衡 ${break_even:.2f}, "
            f"最大收益 ${max_profit:.2f} ({annualized_roi:.1f}% 年化)"
        ),
    )
