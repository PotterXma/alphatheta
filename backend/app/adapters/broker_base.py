"""券商适配器抽象基类 — 所有券商实现都必须遵循此接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BrokerQuote:
    ticker: str
    bid: float
    ask: float
    last: float
    volume: int | None = None


@dataclass
class BrokerOrderResponse:
    broker_order_id: str
    status: str  # filled, pending, rejected
    filled_price: float | None = None
    filled_quantity: int | None = None
    rejection_reason: str | None = None


@dataclass
class BrokerPosition:
    ticker: str
    quantity: int
    avg_cost: float
    current_price: float


class BrokerAdapter(ABC):
    """所有券商适配器的抽象基类"""

    @abstractmethod
    async def get_quote(self, ticker: str) -> BrokerQuote:
        """获取实时报价"""
        ...

    @abstractmethod
    async def get_option_chain(self, ticker: str, expiration: str) -> list[dict]:
        """获取期权链"""
        ...

    @abstractmethod
    async def submit_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str = "limit",
        limit_price: float | None = None,
        strike: float | None = None,
        expiration: str | None = None,
        idempotency_key: str | None = None,
    ) -> BrokerOrderResponse:
        """提交订单 — 必须支持 idempotency_key"""
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """取消订单"""
        ...

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """获取当前持仓"""
        ...

    @abstractmethod
    async def submit_combo_order(
        self,
        ticker: str,
        legs: list[dict],
        net_price: float,
        order_type: str = "limit",
        idempotency_key: str | None = None,
    ) -> BrokerOrderResponse:
        """
        提交原子组合订单 (Combo/Multileg Order)

        关键设计: Buy-Write 必须作为一条原子订单发送给券商，
        绝不能拆分为两个独立订单。拆分会导致"滑腿风险 (Legging Risk)":
        第一腿(买入正股)成交后，市场剧变导致第二腿(卖出期权)无法以预期价格成交。

        参数:
            ticker: 标的代码 (如 SPY)
            legs: 各条腿的参数列表, 每条腿包含:
                - action: BUY/SELL
                - sec_type: STK (股票) / OPT (期权)
                - ratio: 数量比例 (STK=100, OPT=1)
                - option_symbol: OCC 期权代码 (OPT 腿必填)
            net_price: 组合净价 — 整体限价条件
                正值 = Net Debit (买入方净支出)
                负值 = Net Credit (卖出方净收入)
            order_type: 订单类型 (通常为 "limit")
            idempotency_key: 幂等键

        返回:
            BrokerOrderResponse — 包含组合订单的整体状态
        """
        ...

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        """查询订单状态"""
        ...
