"""
订单数据契约 — Pydantic v2 严格校验

设计要点:
1. idempotency_key 作为必填字段 (UUID 格式)，前端负责生成
2. action 使用 StrEnum 限定 BUY/SELL
3. 所有价格字段 ≥ 0，quantity > 0
4. contract_symbol 使用 OCC 期权合约标准格式校验
5. model_config 启用 from_attributes 以兼容 ORM 直接转换
"""

import re
import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderAction(StrEnum):
    """下单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    """订单类型"""
    LIMIT = "limit"
    MARKET = "market"
    LIMIT_PRICE_CHASER = "limit_price_chaser"


# OCC 期权合约代码正则: SPY250418C00525000
_OCC_PATTERN = re.compile(
    r"^[A-Z]{1,6}\d{6}[CP]\d{8}$"
)


class ComboLeg(BaseModel):
    """
    组合订单腿 (Combo Leg) — Buy-Write 原子单的每一条腿

    设计要点:
    - IBKR 使用 conid (合约 ID) + BAG 类型
    - Tradier 使用 option_symbol + multileg 类型
    - ratio 表示该腿的合约乘数关系 (如 STK 100 股 : OPT 1 张)

    Buy-Write 示例:
      Leg 1: action=BUY,  sec_type=STK, ratio=100 (买入 100 股正股)
      Leg 2: action=SELL, sec_type=OPT, ratio=1   (卖出 1 张看涨期权)
    """
    conid: str | None = Field(
        default=None,
        description="合约 ID (IBKR 专用)，Tradier 使用 option_symbol 替代",
    )
    option_symbol: str | None = Field(
        default=None,
        description="OCC 期权合约代码 (Tradier 专用)，如 SPY250418C00525000",
    )
    action: OrderAction = Field(
        ...,
        description="该腿的方向: BUY (买入) 或 SELL (卖出)",
    )
    sec_type: str = Field(
        default="OPT",
        pattern=r"^(STK|OPT)$",
        description="证券类型: STK (股票) 或 OPT (期权)",
    )
    ratio: int = Field(
        default=1,
        gt=0,
        description="该腿的数量比例。STK 腿通常为 100 (100 股)，OPT 腿通常为 1 (1 张合约)",
    )


class OrderCreate(BaseModel):
    """
    创建订单请求 — 前端提交的完整订单参数

    前端必须为每次发单生成唯一的 idempotency_key (UUID v4)，
    后端通过此 Key 保证同一订单不会被重复提交。

    组合订单 (Combo Order):
    - is_combo=True 时，combo_legs 必须非空
    - net_price 代表组合单的净限价 (Net Debit/Credit)
    - 券商适配器会将 combo_legs 打包为原子单，避免滑腿风险
    """
    model_config = {"from_attributes": True}

    idempotency_key: uuid.UUID = Field(
        ...,
        description="幂等键 — 前端生成的 UUID v4，防止网络重试导致重复下单",
    )
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="标的代码，如 SPY、QQQ、AAPL",
        examples=["SPY", "QQQ"],
    )
    contract_symbol: str | None = Field(
        default=None,
        max_length=21,
        description="OCC 期权合约代码，如 SPY250418C00525000。股票订单可为空",
        examples=["SPY250418C00525000"],
    )
    action: OrderAction = Field(
        ...,
        description="下单方向: BUY 或 SELL",
    )
    action_type: str = Field(
        default="Sell Put",
        description="具体策略类型: Sell Put, Sell Call, Buy Stock, Buy-Write",
        examples=["Sell Put", "Sell Call", "Buy Stock", "Buy-Write"],
    )
    order_type: OrderType = Field(
        default=OrderType.LIMIT_PRICE_CHASER,
        description="订单类型: limit (限价), market (市价), limit_price_chaser (追价)",
    )
    quantity: int = Field(
        ...,
        gt=0,
        le=100,
        description="下单数量 (合约张数)，必须 > 0，最大 100",
        examples=[1, 5, 10],
    )
    strike: float | None = Field(
        default=None,
        ge=0,
        description="行权价 (期权)，≥ 0",
        examples=[525.0, 505.0],
    )
    expiration: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="到期日 (YYYY-MM-DD 格式)",
        examples=["2025-04-18"],
    )
    limit_price: float | None = Field(
        default=None,
        ge=0,
        description="限价 (≥ 0)。市价单可为空",
        examples=[5.20, 3.80],
    )

    # ── 组合订单 (Combo Order) 扩展字段 ──

    is_combo: bool = Field(
        default=False,
        description="是否为组合订单 (Buy-Write, Straddle 等需要原子执行的多腿策略)",
    )
    combo_legs: list[ComboLeg] = Field(
        default_factory=list,
        description="组合订单的各条腿。is_combo=True 时必须非空",
    )
    net_price: float | None = Field(
        default=None,
        description=(
            "组合单净价 (Net Debit/Credit)。"
            "正值 = Net Debit (支出), 负值 = Net Credit (收入)。"
            "Buy-Write 示例: (SPY $505.20 - Call $5.20) = $500.00 净支出"
        ),
        examples=[500.0, -3.80],
    )

    # ── 字段级校验 ──

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        """Ticker 统一大写"""
        return v.upper().strip()

    @field_validator("contract_symbol")
    @classmethod
    def validate_occ_format(cls, v: str | None) -> str | None:
        """校验 OCC 期权合约代码格式"""
        if v is None:
            return v
        v = v.upper().strip()
        if not _OCC_PATTERN.match(v):
            raise ValueError(
                f"Invalid OCC contract symbol: '{v}'. "
                f"Expected format: SPY250418C00525000"
            )
        return v

    # ── 模型级校验 ──

    @model_validator(mode="after")
    def check_option_fields(self):
        """期权订单必须同时提供 strike 和 expiration"""
        has_contract = self.contract_symbol is not None
        has_strike = self.strike is not None
        has_exp = self.expiration is not None

        if has_contract and not (has_strike and has_exp):
            raise ValueError(
                "Option orders require both 'strike' and 'expiration' fields"
            )
        return self

    @model_validator(mode="after")
    def check_combo_fields(self):
        """组合订单必须提供 combo_legs"""
        if self.is_combo and not self.combo_legs:
            raise ValueError(
                "Combo orders (is_combo=True) require at least 2 combo_legs. "
                "Buy-Write needs: [STK BUY 100, OPT SELL 1]"
            )
        if self.is_combo and self.net_price is None:
            raise ValueError(
                "Combo orders require net_price (组合净价). "
                "Calculate: (underlying_price - option_premium) for Buy-Write"
            )
        return self


class OrderResponse(BaseModel):
    """订单响应 — 从 ORM 模型序列化"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    idempotency_key: str | None = None
    ticker: str
    action_type: str
    order_type: str
    strike: float | None = None
    expiration: str | None = None
    quantity: int
    limit_price: float | None = None
    status: str
    broker_order_id: str | None = None
    filled_price: float | None = None
    filled_quantity: int | None = None
    filled_at: datetime | None = None
    rejection_reason: str | None = None
    env_mode: str
    created_at: datetime
    updated_at: datetime


class PositionResponse(BaseModel):
    """持仓响应"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    ticker: str
    quantity: int
    avg_cost_basis: float
    current_value: float | None = None
    unrealized_pnl: float | None = None
    env_mode: str
    updated_at: datetime


class RollRequest(BaseModel):
    """展期请求"""
    position_id: uuid.UUID
    roll_type: str = Field(
        ...,
        pattern=r"^(up|down|out)$",
        description="展期方向: up (上移 Strike), down (下移), out (延期)",
    )


class RollResponse(BaseModel):
    """展期计算结果"""
    original_strike: float
    new_strike: float
    new_expiration: str
    estimated_credit_or_debit: float
    roll_type: str
