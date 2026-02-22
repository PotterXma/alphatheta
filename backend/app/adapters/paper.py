"""Paper Broker Adapter — 本地模拟，用于 Paper 模式"""

import asyncio
import random
import uuid

from app.adapters.broker_base import (
    BrokerAdapter,
    BrokerOrderResponse,
    BrokerPosition,
    BrokerQuote,
)


class PaperBrokerAdapter(BrokerAdapter):
    """模拟券商: 本地模拟 fill，不发真实请求"""

    def __init__(self):
        self._positions: dict[str, BrokerPosition] = {}
        self._orders: dict[str, BrokerOrderResponse] = {}

    async def get_quote(self, ticker: str) -> BrokerQuote:
        # 模拟报价
        base = {"SPY": 505.0, "QQQ": 438.0, "AAPL": 228.0}.get(ticker, 100.0)
        spread = base * 0.001
        return BrokerQuote(
            ticker=ticker,
            bid=round(base - spread, 2),
            ask=round(base + spread, 2),
            last=round(base, 2),
            volume=random.randint(100000, 5000000),
        )

    async def get_option_chain(self, ticker: str, expiration: str) -> list[dict]:
        return []  # Paper 模式不返回期权链

    async def submit_order(
        self, ticker: str, action: str, quantity: int,
        order_type: str = "limit", limit_price: float | None = None,
        strike: float | None = None, expiration: str | None = None,
        idempotency_key: str | None = None,
    ) -> BrokerOrderResponse:
        # 模拟 50-200ms 延迟后 fill
        await asyncio.sleep(random.uniform(0.05, 0.2))
        order_id = str(uuid.uuid4())[:8]
        fill_price = limit_price or 5.0

        resp = BrokerOrderResponse(
            broker_order_id=order_id,
            status="filled",
            filled_price=fill_price,
            filled_quantity=quantity,
        )
        self._orders[order_id] = resp
        return resp

    async def cancel_order(self, broker_order_id: str) -> bool:
        return broker_order_id in self._orders

    async def get_positions(self) -> list[BrokerPosition]:
        return list(self._positions.values())

    async def submit_combo_order(
        self, ticker: str, legs: list[dict], net_price: float,
        order_type: str = "limit", idempotency_key: str | None = None,
    ) -> BrokerOrderResponse:
        """模拟组合单: 记录所有腿 + 模拟 fill"""
        await asyncio.sleep(random.uniform(0.05, 0.2))
        order_id = f"COMBO-{str(uuid.uuid4())[:8]}"
        self._orders[order_id] = BrokerOrderResponse(
            broker_order_id=order_id,
            status="filled",
            filled_price=net_price,
            filled_quantity=1,
        )
        return self._orders[order_id]

    async def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        return self._orders.get(
            broker_order_id,
            BrokerOrderResponse(broker_order_id=broker_order_id, status="unknown"),
        )
