"""
OMS 追单引擎 — 部分成交 (Partial Fill) 监控与补偿

设计要点:
1. 定期扫描 Submitted 状态超过 3 分钟的组合单
2. 检测"滑腿"风险: 正股已买但期权未卖出 → 裸露多头敞口
3. 触发 NotificationService 报警
4. 生成 Cancel & Replace 补偿操作建议
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from app.services.notifier import get_notifier

logger = logging.getLogger("alphatheta.order_chaser")


class ChaserAction(StrEnum):
    """追单引擎可执行的操作"""
    CANCEL_REPLACE = "cancel_replace"   # 撤单重发 (调整价格)
    FORCE_CANCEL = "force_cancel"       # 强制撤单 (放弃本次)
    MANUAL_REVIEW = "manual_review"     # 人工复核 (复杂情况)


class OrderChaserService:
    """
    订单追逐者 — 防止组合单部分成交导致的敞口风险

    核心场景:
    - Buy-Write 组合单: 正股 BUY 已 Filled, Call SELL 未成交
      → 持有裸露多头, 无备兑保护, 如果市场突然下跌会全额亏损
    - 解决方案: 检测 > 3min 的 Submitted 订单, 触发报警 + 补偿建议

    调用方式:
    - 由 APScheduler 定时任务每 60 秒调用一次
    - 或由 WebSocket 事件驱动 (券商推送 partial fill)
    """

    # 部分成交超时阈值 (秒)
    STALE_THRESHOLD_SECONDS = 180  # 3 分钟

    def __init__(self):
        self._notifier = get_notifier()

    async def check_and_chase_orders(self, open_orders: list[dict]) -> list[dict]:
        """
        扫描并处理过期的组合订单

        参数:
            open_orders: 当前所有 Submitted 状态的订单列表
                每条订单需包含:
                - order_id: str
                - ticker: str
                - is_combo: bool
                - combo_legs: list[dict] (每条腿的状态)
                - submitted_at: datetime
                - status: str

        返回:
            list[dict] — 补偿操作建议列表
        """
        now = datetime.now(timezone.utc)
        recommendations = []

        for order in open_orders:
            if not order.get("is_combo"):
                continue

            submitted_at = order.get("submitted_at")
            if not submitted_at:
                continue

            # ── 检查是否超时 ──
            elapsed = (now - submitted_at).total_seconds()
            if elapsed < self.STALE_THRESHOLD_SECONDS:
                continue

            # ── 检查腿部成交状态 ──
            legs = order.get("combo_legs", [])
            filled_legs = [l for l in legs if l.get("status") == "filled"]
            unfilled_legs = [l for l in legs if l.get("status") != "filled"]

            if not filled_legs or not unfilled_legs:
                # 全部成交或全部未成交 — 不需要追单
                continue

            # ── 滑腿检测: 部分成交 → 敞口风险 ──
            ticker = order.get("ticker", "UNKNOWN")
            order_id = order.get("order_id", "N/A")

            filled_desc = ", ".join(
                f"{l.get('sec_type', '?')} {l.get('action', '?')} x{l.get('ratio', 1)}"
                for l in filled_legs
            )
            unfilled_desc = ", ".join(
                f"{l.get('sec_type', '?')} {l.get('action', '?')} x{l.get('ratio', 1)}"
                for l in unfilled_legs
            )

            logger.warning(
                f"[OrderChaser] PARTIAL FILL detected! "
                f"Order={order_id}, Ticker={ticker}, "
                f"Elapsed={elapsed:.0f}s, "
                f"Filled=[{filled_desc}], Unfilled=[{unfilled_desc}]"
            )

            # ── 生成补偿建议 ──
            recommendation = self._generate_recommendation(
                order_id=order_id,
                ticker=ticker,
                elapsed_seconds=elapsed,
                filled_legs=filled_legs,
                unfilled_legs=unfilled_legs,
            )
            recommendations.append(recommendation)

            # ── 触发容灾报警 ──
            await self._notifier.send_critical_alert(
                title="⚠ 组合单部分成交 — 滑腿风险",
                message=(
                    f"订单 {order_id} 已提交 {elapsed:.0f} 秒, "
                    f"仅部分腿成交。\n"
                    f"已成交: [{filled_desc}]\n"
                    f"未成交: [{unfilled_desc}]\n"
                    f"建议操作: {recommendation['action']}"
                ),
                ticker=ticker,
                severity="CRITICAL",
            )

        return recommendations

    def _generate_recommendation(
        self,
        order_id: str,
        ticker: str,
        elapsed_seconds: float,
        filled_legs: list[dict],
        unfilled_legs: list[dict],
    ) -> dict:
        """
        根据部分成交的腿生成补偿操作建议

        策略:
        - 正股已买 + 期权未卖: Cancel & Replace (调宽期权价格)
        - 超过 10 分钟: 强制撤单, 人工介入
        - 其他: 人工复核
        """
        # 判断正股腿是否已成交
        stock_filled = any(
            l.get("sec_type") == "STK" and l.get("status") == "filled"
            for l in filled_legs
        )
        option_unfilled = any(
            l.get("sec_type") == "OPT" and l.get("status") != "filled"
            for l in unfilled_legs
        )

        if elapsed_seconds > 600:
            # 超过 10 分钟 — 强制撤单, 需要人工清理敞口
            action = ChaserAction.FORCE_CANCEL
            reason = "超过 10 分钟未完全成交, 强制撤单防止更大敞口"
        elif stock_filled and option_unfilled:
            # 经典滑腿: 正股已买, 期权还没卖出
            # 建议: 撤单原期权腿, 重新以市场价提交
            action = ChaserAction.CANCEL_REPLACE
            reason = (
                "正股已成交但期权未成交 — 当前持有裸露多头。"
                "建议: 撤销未成交的期权腿, 以当前市场中间价重新提交"
            )
        else:
            # 其他复杂情况
            action = ChaserAction.MANUAL_REVIEW
            reason = "部分成交情况复杂, 需人工审核"

        return {
            "order_id": order_id,
            "ticker": ticker,
            "action": action.value,
            "reason": reason,
            "elapsed_seconds": round(elapsed_seconds),
            "filled_legs": len(filled_legs),
            "unfilled_legs": len(unfilled_legs),
        }
