"""Tradier REST Adapter — 首期券商实现, 含重试 + 熔断"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.adapters.broker_base import (
    BrokerAdapter,
    BrokerOrderResponse,
    BrokerPosition,
    BrokerQuote,
)

logger = logging.getLogger("alphatheta.tradier")


@dataclass
class CircuitBreakerState:
    """熔断器: 5 次连续 429 → 打开 30s"""

    consecutive_429s: int = 0
    open_until: float = 0.0  # timestamp
    THRESHOLD: int = 5
    COOLDOWN_SECONDS: float = 30.0

    @property
    def is_open(self) -> bool:
        return time.time() < self.open_until

    def record_429(self) -> None:
        self.consecutive_429s += 1
        if self.consecutive_429s >= self.THRESHOLD:
            self.open_until = time.time() + self.COOLDOWN_SECONDS
            logger.warning(f"Circuit breaker OPEN for {self.COOLDOWN_SECONDS}s")

    def record_success(self) -> None:
        self.consecutive_429s = 0


class TradierAdapter(BrokerAdapter):
    """Tradier REST API 适配器"""

    MAX_RETRIES = 3
    BACKOFF_BASE = 1.0  # seconds

    def __init__(self, api_key: str, base_url: str = "https://sandbox.tradier.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.circuit_breaker = CircuitBreakerState()
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            timeout=10.0,
        )

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """带重试 + 熔断的 HTTP 请求"""
        if self.circuit_breaker.is_open:
            raise RuntimeError("Circuit breaker is OPEN — broker API temporarily unavailable")

        for attempt in range(self.MAX_RETRIES):
            try:
                resp = await self._client.request(method, path, **kwargs)

                if resp.status_code == 429:
                    self.circuit_breaker.record_429()
                    wait = self.BACKOFF_BASE * (2**attempt)
                    logger.warning(f"Broker 429, retry {attempt + 1}/{self.MAX_RETRIES} in {wait}s")
                    await asyncio.sleep(wait)
                    continue

                self.circuit_breaker.record_success()
                resp.raise_for_status()
                return resp.json()

            except httpx.TimeoutException:
                wait = self.BACKOFF_BASE * (2**attempt)
                logger.warning(f"Broker timeout, retry {attempt + 1}/{self.MAX_RETRIES} in {wait}s")
                await asyncio.sleep(wait)

        raise RuntimeError(f"Broker API failed after {self.MAX_RETRIES} retries")

    async def get_quote(self, ticker: str) -> BrokerQuote:
        data = await self._request("GET", f"/markets/quotes", params={"symbols": ticker})
        q = data.get("quotes", {}).get("quote", {})
        return BrokerQuote(
            ticker=ticker,
            bid=q.get("bid", 0),
            ask=q.get("ask", 0),
            last=q.get("last", 0),
            volume=q.get("volume"),
        )

    async def get_option_chain(self, ticker: str, expiration: str) -> list[dict]:
        data = await self._request(
            "GET", "/markets/options/chains",
            params={"symbol": ticker, "expiration": expiration},
        )
        return data.get("options", {}).get("option", [])

    async def submit_order(
        self, ticker: str, action: str, quantity: int,
        order_type: str = "limit", limit_price: float | None = None,
        strike: float | None = None, expiration: str | None = None,
        idempotency_key: str | None = None,
    ) -> BrokerOrderResponse:
        payload = {
            "class": "option" if strike else "equity",
            "symbol": ticker,
            "side": action.lower(),
            "quantity": str(quantity),
            "type": order_type,
            "duration": "day",
        }
        if limit_price:
            payload["price"] = str(limit_price)
        if strike:
            # Tradier option symbol format
            payload["option_symbol"] = f"{ticker}{expiration}{int(strike * 1000):08d}"

        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        data = await self._request("POST", "/accounts/orders", data=payload, headers=headers)
        order = data.get("order", {})
        return BrokerOrderResponse(
            broker_order_id=str(order.get("id", "")),
            status=order.get("status", "pending"),
        )

    async def cancel_order(self, broker_order_id: str) -> bool:
        try:
            await self._request("DELETE", f"/accounts/orders/{broker_order_id}")
            return True
        except Exception:
            return False

    async def get_positions(self) -> list[BrokerPosition]:
        data = await self._request("GET", "/accounts/positions")
        positions = data.get("positions", {}).get("position", [])
        if isinstance(positions, dict):
            positions = [positions]
        return [
            BrokerPosition(
                ticker=p.get("symbol", ""),
                quantity=p.get("quantity", 0),
                avg_cost=p.get("cost_basis", 0) / max(p.get("quantity", 1), 1),
                current_price=p.get("last_price", 0),
            )
            for p in positions
        ]

    async def submit_combo_order(
        self, ticker: str, legs: list[dict], net_price: float,
        order_type: str = "limit", idempotency_key: str | None = None,
    ) -> BrokerOrderResponse:
        """
        Tradier Multileg 组合订单 — 原子执行 Buy-Write

        Tradier API 使用 class=multileg 来发送组合订单。
        关键点:
        1. 所有腿打包在一个 HTTP 请求中 → 原子执行
        2. 券商内部引擎保证要么全部成交、要么全部取消
        3. net_price 作为整体限价，而非每条腿单独定价

        Buy-Write Payload 示例:
        {
            "class": "multileg",
            "symbol": "SPY",
            "type": "debit",           ← 净支出 (买股 - 卖 Call)
            "duration": "day",
            "price": "500.00",          ← 净价 = 正股价 - 期权权利金
            "option_symbol[0]": "SPY",  ← Leg 1: 正股 (Tradier 用 symbol 直接代表)
            "side[0]": "buy",
            "quantity[0]": "100",       ← 100 股
            "option_symbol[1]": "SPY260403C00525000",  ← Leg 2: OCC 期权代码
            "side[1]": "sell_to_open",  ← 卖出开仓
            "quantity[1]": "1",         ← 1 张合约 (= 100 股)
        }

        净价 (Net Price) 公式:
        - Buy-Write: net_price = underlying_price - call_premium
          例: SPY $505.20 - Call $5.20 = $500.00 (净支出 $50,000)
        - 正值 = Net Debit (买方净支出)
        - 负值 = Net Credit (卖方净收入)

        比例 (Ratio) 设计:
        - STK 腿 ratio=100: 1 手正股 = 100 股 (与 1 张期权覆盖的股数对应)
        - OPT 腿 ratio=1:   1 张合约覆盖 100 股
        - 两腿比例必须匹配，否则会出现 "裸露" 风险
        """
        # ── 构建 Multileg Payload ──
        payload: dict[str, str] = {
            "class": "multileg",
            "symbol": ticker,
            "type": "debit" if net_price >= 0 else "credit",
            "duration": "day",
            "price": str(abs(round(net_price, 2))),
        }

        # ── 添加每条腿 ──
        for i, leg in enumerate(legs):
            sec_type = leg.get("sec_type", "OPT")
            action = leg.get("action", "BUY").lower()
            ratio = leg.get("ratio", 1)

            if sec_type == "STK":
                # 正股腿: 使用 ticker 作为 option_symbol
                payload[f"option_symbol[{i}]"] = ticker
                payload[f"side[{i}]"] = "buy" if action == "buy" else "sell"
                payload[f"quantity[{i}]"] = str(ratio)  # 通常 100
            else:
                # 期权腿: 使用 OCC 合约代码
                option_sym = leg.get("option_symbol", "")
                payload[f"option_symbol[{i}]"] = option_sym
                # Tradier 区分 sell_to_open / sell_to_close
                if action == "sell":
                    payload[f"side[{i}]"] = "sell_to_open"
                else:
                    payload[f"side[{i}]"] = "buy_to_open"
                payload[f"quantity[{i}]"] = str(ratio)  # 通常 1

        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        logger.info(f"Submitting multileg combo order: {payload}")
        data = await self._request("POST", "/accounts/orders", data=payload, headers=headers)
        order = data.get("order", {})
        return BrokerOrderResponse(
            broker_order_id=str(order.get("id", "")),
            status=order.get("status", "pending"),
        )

    async def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        data = await self._request("GET", f"/accounts/orders/{broker_order_id}")
        order = data.get("order", {})
        return BrokerOrderResponse(
            broker_order_id=broker_order_id,
            status=order.get("status", "unknown"),
            filled_price=order.get("avg_fill_price"),
            filled_quantity=order.get("exec_quantity"),
        )
