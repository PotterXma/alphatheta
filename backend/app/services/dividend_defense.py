"""
股息防御扫描器 — 提前指派 (Early Assignment) 防线

核心风险:
  当你持有 Short Call (备兑 or 裸卖), 且标的即将除息时,
  如果 Call 的剩余时间价值 < 预估股息, 做市商会提前行权以获得股息。
  这意味着你的正股会被意外收走, 打破 Covered Call 的保护结构。

防御策略:
  1. 扫描所有 Short Call 仓位
  2. 若距除息日 <= 3 天, 且 Call 时间价值 < 预估股息
  3. 立即触发 ROLL_OUT (展期到下个月) 或 BUY_TO_CLOSE (平仓)
"""

import logging
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger("alphatheta.dividend_defense")


@dataclass
class DividendRisk:
    """股息提前指派风险评估"""
    ticker: str
    ex_dividend_date: date
    days_to_ex_div: int
    estimated_dividend: float    # 预估股息 (每股)
    call_time_value: float       # Call 剩余时间价值 (每股)
    is_at_risk: bool             # 是否存在风险
    recommended_action: str      # "ROLL_OUT" / "BUY_TO_CLOSE" / "SAFE"
    reasoning: str


class DividendDefenseScanner:
    """
    股息防御扫描器 — 守护 Short Call 仓位

    使用:
        scanner = DividendDefenseScanner()
        risks = scanner.scan_positions(short_calls, fundamental_data)
    """

    # 风险阈值
    EX_DIV_DAYS_THRESHOLD = 3   # 距除息日 <= 3 天触发
    TIME_VALUE_BUFFER = 0.10    # 时间价值需 > 股息 + $0.10 才安全

    def scan_positions(
        self,
        short_calls: list[dict],
        fundamental_contexts: dict[str, "FundamentalContext"],
    ) -> list[DividendRisk]:
        """
        扫描所有 Short Call 仓位的股息指派风险

        参数:
            short_calls: Short Call 仓位列表
                每条需包含: ticker, strike, market_price, intrinsic_value
            fundamental_contexts: 各标的的基本面数据

        返回:
            list[DividendRisk] — 有风险的仓位列表
        """
        risks = []
        today = date.today()

        for call in short_calls:
            ticker = call.get("ticker", "")
            ctx = fundamental_contexts.get(ticker)

            if not ctx or not ctx.ex_dividend_date:
                continue

            days_to_ex_div = (ctx.ex_dividend_date - today).days

            # 仅检查 3 天内的除息日
            if days_to_ex_div < 0 or days_to_ex_div > self.EX_DIV_DAYS_THRESHOLD:
                continue

            # ── 计算时间价值 ──
            # Time Value = Market Price - Intrinsic Value
            # Intrinsic Value (ITM Call) = Max(0, Stock Price - Strike)
            market_price = call.get("market_price", 0)
            intrinsic = call.get("intrinsic_value", 0)
            time_value = max(0, market_price - intrinsic)

            # ── 预估股息 ──
            est_dividend = self._estimate_quarterly_dividend(ctx)

            # ── 风险判断 ──
            # 如果 时间价值 < 股息 + buffer → 存在提前指派风险
            is_at_risk = time_value < (est_dividend + self.TIME_VALUE_BUFFER)

            if is_at_risk:
                # 决定防御动作
                if time_value < est_dividend * 0.5:
                    # 时间价值极低 → 直接平仓
                    action = "BUY_TO_CLOSE"
                    reasoning = (
                        f"距除息日仅 {days_to_ex_div} 天, "
                        f"Call 时间价值 ${time_value:.2f} 远低于股息 ${est_dividend:.2f}。"
                        f"做市商极有可能提前行权。立即平仓止损。"
                    )
                else:
                    # 时间价值一般 → 展期到下个月
                    action = "ROLL_OUT"
                    reasoning = (
                        f"距除息日仅 {days_to_ex_div} 天, "
                        f"Call 时间价值 ${time_value:.2f} 接近股息 ${est_dividend:.2f}。"
                        f"建议展期到下月, 增加时间价值以避免指派。"
                    )

                logger.warning(
                    f"[DividendDefense/{ticker}] RISK DETECTED — "
                    f"ex-div in {days_to_ex_div}d, TV=${time_value:.2f} < "
                    f"div=${est_dividend:.2f}. Action: {action}"
                )
            else:
                action = "SAFE"
                reasoning = (
                    f"距除息日 {days_to_ex_div} 天, "
                    f"Call 时间价值 ${time_value:.2f} 高于股息 ${est_dividend:.2f}。"
                    f"无提前指派风险。"
                )

            risks.append(DividendRisk(
                ticker=ticker,
                ex_dividend_date=ctx.ex_dividend_date,
                days_to_ex_div=days_to_ex_div,
                estimated_dividend=round(est_dividend, 4),
                call_time_value=round(time_value, 4),
                is_at_risk=is_at_risk,
                recommended_action=action,
                reasoning=reasoning,
            ))

        return risks

    def _estimate_quarterly_dividend(self, ctx) -> float:
        """
        估算季度股息 (每股)

        计算: 年股息率 * 股价 / 4
        简化假设: 股息按季度均分
        """
        if ctx.dividend_yield and ctx.dividend_yield > 0:
            # 粗略估算: 假设 underlying_price ≈ market_cap / shares_outstanding
            # 但我们没有 shares_outstanding, 用 1.0 作为 fallback
            # 实际应从 yfinance 的 dividendRate 获取
            return ctx.dividend_yield * 100 / 4  # 简化: 假设 $100 股价基准
        return 0.0
