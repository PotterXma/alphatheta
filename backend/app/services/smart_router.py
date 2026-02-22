"""
智能订单路由 (Smart Order Router) — Price Walking 微调引擎

实盘核心问题:
  期权市场 bid-ask spread 通常 $0.05-$0.20。
  直接挂 Mid Price 可能永远不成交, 直接挂 Market 会被做市商剃头。

解决方案 — Price Walking:
  1. 从 Mid Price 开始挂限价单
  2. 每 15 秒检查一次, 若未成交则撤单
  3. 向对手价方向妥协 $0.01, 重新提交
  4. 循环直至触及 Floor Price (用户可接受的最差价格)
  5. 若触及 Floor 仍未成交, 放弃并报警

设计要点:
  - asyncio.Lock 防止同一标的多个 walking 并发
  - 每次重挂单记录审计日志
  - 总超时 120 秒兜底
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import StrEnum

from app.services.notifier import get_notifier

logger = logging.getLogger("alphatheta.smart_router")


class WalkResult(StrEnum):
    """Price Walking 结果"""
    FILLED = "filled"
    FLOOR_REACHED = "floor_reached"
    TIMEOUT = "timeout"
    ERROR = "error"


class SmartOrderRouter:
    """
    智能订单路由器 — Price Walking 循环

    使用:
        router = SmartOrderRouter(broker_adapter)
        result = await router.execute_with_price_walking(
            ticker="SPY",
            side="sell",
            quantity=1,
            option_symbol="SPY250321C00510000",
            mid_price=5.20,
            floor_price=5.10,
        )
    """

    # Walking 参数
    STEP_SIZE = 0.01           # 每次妥协幅度 ($)
    CHECK_INTERVAL = 15        # 检查间隔 (秒)
    MAX_TOTAL_TIMEOUT = 120    # 总超时 (秒)

    def __init__(self, broker_adapter=None):
        self._broker = broker_adapter
        self._notifier = get_notifier()
        self._walking_locks: dict[str, asyncio.Lock] = {}  # 每个标的独立锁

    def _get_lock(self, ticker: str) -> asyncio.Lock:
        """获取标的级别的异步锁 — 防止同一标的多个 walking 并发"""
        if ticker not in self._walking_locks:
            self._walking_locks[ticker] = asyncio.Lock()
        return self._walking_locks[ticker]

    async def execute_with_price_walking(
        self,
        ticker: str,
        side: str,          # "buy" or "sell"
        quantity: int,
        option_symbol: str,
        mid_price: float,
        floor_price: float,
    ) -> dict:
        """
        Price Walking 主循环

        参数:
            ticker: 标的代码
            side: 买卖方向
            quantity: 合约数量
            option_symbol: 期权合约符号
            mid_price: 起始挂单价 (Mid Price)
            floor_price: 最差可接受价格 (Floor)

        返回:
            dict — { result, final_price, steps, elapsed }
        """
        lock = self._get_lock(ticker)

        async with lock:
            return await self._walk(
                ticker=ticker,
                side=side,
                quantity=quantity,
                option_symbol=option_symbol,
                mid_price=mid_price,
                floor_price=floor_price,
            )

    async def _walk(
        self,
        ticker: str,
        side: str,
        quantity: int,
        option_symbol: str,
        mid_price: float,
        floor_price: float,
    ) -> dict:
        """内部 Walking 循环实现"""
        current_price = mid_price
        step_count = 0
        start_time = datetime.now(timezone.utc)
        order_id = None
        audit_trail: list[dict] = []

        # 方向系数: sell 时向下走 (逐步降价), buy 时向上走 (逐步加价)
        direction = -1 if side == "sell" else 1

        logger.info(
            f"[SmartRouter/{ticker}] Starting price walk: "
            f"side={side}, mid=${mid_price:.2f}, floor=${floor_price:.2f}"
        )

        while True:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            # ── 总超时检查 ──
            if elapsed > self.MAX_TOTAL_TIMEOUT:
                logger.warning(f"[SmartRouter/{ticker}] Total timeout reached ({elapsed:.0f}s)")
                if order_id:
                    await self._cancel_order(order_id)
                return {
                    "result": WalkResult.TIMEOUT,
                    "final_price": current_price,
                    "steps": step_count,
                    "elapsed": round(elapsed, 1),
                    "audit": audit_trail,
                }

            # ── Floor Price 检查 ──
            if (side == "sell" and current_price < floor_price) or \
               (side == "buy" and current_price > floor_price):
                logger.warning(
                    f"[SmartRouter/{ticker}] Floor reached @ ${current_price:.2f}"
                )
                await self._notifier.send_critical_alert(
                    title="Price Walking 触及底价",
                    message=(
                        f"{ticker} {option_symbol}: "
                        f"从 ${mid_price:.2f} 走到 ${current_price:.2f}, "
                        f"已触及 Floor ${floor_price:.2f}, 放弃本次挂单"
                    ),
                    ticker=ticker,
                    severity="WARNING",
                )
                return {
                    "result": WalkResult.FLOOR_REACHED,
                    "final_price": current_price,
                    "steps": step_count,
                    "elapsed": round(elapsed, 1),
                    "audit": audit_trail,
                }

            # ── 提交/重挂限价单 ──
            step_count += 1
            audit_entry = {
                "step": step_count,
                "price": round(current_price, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if self._broker:
                # 真实模式: 提交到券商
                if order_id:
                    await self._cancel_order(order_id)
                order_id = await self._submit_limit_order(
                    ticker, side, quantity, option_symbol, current_price
                )
                audit_entry["order_id"] = order_id
            else:
                # 模拟模式: 日志记录
                logger.info(
                    f"[SmartRouter/{ticker}] Step {step_count}: "
                    f"{'Resubmit' if step_count > 1 else 'Submit'} "
                    f"@ ${current_price:.2f}"
                )

            audit_trail.append(audit_entry)

            # ── 等待成交 ──
            await asyncio.sleep(self.CHECK_INTERVAL)

            # ── 检查是否成交 ──
            if self._broker and order_id:
                status = await self._check_order_status(order_id)
                if status == "filled":
                    logger.info(
                        f"[SmartRouter/{ticker}] FILLED @ ${current_price:.2f} "
                        f"after {step_count} steps ({elapsed:.0f}s)"
                    )
                    return {
                        "result": WalkResult.FILLED,
                        "final_price": current_price,
                        "steps": step_count,
                        "elapsed": round(elapsed, 1),
                        "audit": audit_trail,
                    }
            else:
                # 模拟模式: 随机模拟成交 (步数 >= 3 时 50% 概率)
                import random
                if step_count >= 3 and random.random() > 0.5:
                    return {
                        "result": WalkResult.FILLED,
                        "final_price": current_price,
                        "steps": step_count,
                        "elapsed": round(elapsed, 1),
                        "audit": audit_trail,
                    }

            # ── 妥协一步 ──
            current_price = round(current_price + direction * self.STEP_SIZE, 2)

    async def _submit_limit_order(self, ticker, side, qty, symbol, price) -> str:
        """提交限价单到券商 — 返回 order_id"""
        # TODO: 接入 TradierAdapter.submit_order()
        return f"SIM-{ticker}-{price}"

    async def _cancel_order(self, order_id: str):
        """撤单"""
        logger.info(f"[SmartRouter] Cancelling order {order_id}")
        # TODO: 接入 TradierAdapter.cancel_order()

    async def _check_order_status(self, order_id: str) -> str:
        """查询订单状态"""
        # TODO: 接入 TradierAdapter.get_order_status()
        return "pending"
