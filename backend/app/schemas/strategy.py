"""
策略与择时引擎 — 数据契约 (DTOs)

数据流:
  MarketDataService → StrategyMarketContext → StrategyEntryEngine → TimingDecision
  PositionService   → PositionSnapshot      → LifecycleScannerEngine → [TimingDecision]
                                                                       ↓
                                                              OrderManagerService
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


# ══════════════════════════════════════════════════════════════════
# 枚举
# ══════════════════════════════════════════════════════════════════


class ActionType(StrEnum):
    """
    交易动作类型

    期权对冲系统的六种核心操作:
    - SELL_PUT:      卖出看跌期权 (赚取权利金, 承诺底部接盘)
    - SELL_CALL:     卖出看涨期权 / 备兑开仓 (赚取权利金, 有上限)
    - BUY_WRITE:     买入正股 + 同时卖出看涨期权 (Buy-Write 组合建仓)
    - BUY_TO_CLOSE:  买入平仓 (对已卖出的期权进行平仓, 止盈/止损)
    - ROLL_OUT:      展期 (平掉近月合约, 卖出远月合约, 延长时间价值)
    - HOLD:          观望 / 不操作 (等待更好的入场时机)
    """
    SELL_PUT = "sell_put"
    SELL_CALL = "sell_call"
    BUY_WRITE = "buy_write"
    BUY_TO_CLOSE = "buy_to_close"
    ROLL_OUT = "roll_out"
    HOLD = "hold"


# ══════════════════════════════════════════════════════════════════
# 期权链合约快照
# ══════════════════════════════════════════════════════════════════


class OptionContract(BaseModel):
    """
    期权链中的单个合约快照

    字段对齐 Tradier API /markets/options/chains 返回格式:
    https://documentation.tradier.com/brokerage-api/markets/get-options-chains

    Delta / Gamma 等希腊字母由券商或第三方 API 提供 (如 Tradier, CBOE)
    """
    symbol: str = Field(..., description="OCC 格式合约代码, 如 SPY250321P00500000")
    strike: float = Field(..., gt=0, description="行权价")
    expiration: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="到期日 YYYY-MM-DD")
    option_type: str = Field(..., pattern=r"^(put|call)$", description="put 或 call")
    bid: float = Field(..., ge=0, description="最优买价")
    ask: float = Field(..., ge=0, description="最优卖价")
    last: float = Field(default=0.0, ge=0, description="最新成交价")

    # ── 希腊字母 (Greeks) ──
    # Delta: 标的价格变动 $1 时, 期权价格变动多少
    #   - Put Delta 通常为负值 (-1 ~ 0), 这里取绝对值方便比较
    #   - Delta ≈ 0.16 意味着被行权概率约 16% (即 84% 胜率)
    delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Delta (标的敏感度)")

    # Gamma: Delta 的变化速率, DTE < 21 天时 Gamma 急剧上升 (Gamma 爆炸)
    gamma: float = Field(default=0.0, ge=0.0, description="Gamma (Delta 加速度)")

    # ── 流动性指标 ──
    open_interest: int = Field(default=0, ge=0, description="未平仓合约数 (OI)")
    volume: int = Field(default=0, ge=0, description="当日成交量")

    @property
    def mid_price(self) -> float:
        """中间价 — 实际挂单参考价"""
        return round((self.bid + self.ask) / 2, 2)

    @property
    def spread_pct(self) -> float:
        """Bid/Ask 价差百分比 — 流动性指标, > 8% 视为流动性不足"""
        if self.ask == 0:
            return 0.0
        return round((self.ask - self.bid) / self.ask * 100, 2)


# ══════════════════════════════════════════════════════════════════
# 策略引擎输入: 市场上下文 (扩展版)
# ══════════════════════════════════════════════════════════════════


class StrategyMarketContext(BaseModel):
    """
    策略引擎专用的市场上下文

    与 schemas/market.py 中的 MarketContext 区别:
    - MarketContext: 面向前端 Dashboard 展示, 字段偏展示型
    - StrategyMarketContext: 面向策略引擎决策, 包含期权链 + 持仓标记 + 财报日

    两者共享 vix / rsi_14 等底层字段, 但本类多出:
    1. has_position — 是否已有该标的持仓 (影响 Scene A/B/D 决策路径)
    2. earnings_date — 最近财报日 (3 天内强制 HOLD, 规避 IV Crush)
    3. options_chain — 当前期权链快照 (用于 Delta 寻优 + 流动性过滤)
    """
    ticker: str = Field(..., description="标的代码")
    underlying_price: float = Field(..., gt=0, description="标的当前价格")

    # ── 宏观 + 技术指标 ──
    vix: float = Field(..., ge=0, le=100, description="VIX 恐慌指数")
    rsi_14: float = Field(..., ge=0, le=100, description="RSI-14")

    # ── 持仓状态 ──
    has_position: bool = Field(
        default=False,
        description="是否已持有该标的正股 (影响备兑/卖Put决策)",
    )
    current_position_qty: int = Field(
        default=0,
        description="当前持仓数量 (用于判断 Buy-Write 的可行性)",
    )

    # ── 事件日历 ──
    earnings_date: date | None = Field(
        default=None,
        description=(
            "最近一次财报发布日。距离 < 3 天时强制 HOLD, "
            "因为财报会导致 IV Crush (隐含波动率在财报后骤降, "
            "期权卖方在财报前建仓的风险集中在方向猜错上)"
        ),
    )

    # ── 期权链 ──
    options_chain: list[OptionContract] = Field(
        default_factory=list,
        description="当前可交易的期权合约列表 (已按到期日和行权价过滤)",
    )

    # ── 可用资金 ──
    available_cash: float = Field(
        default=0.0, ge=0,
        description="可用现金, 影响建仓规模",
    )


# ══════════════════════════════════════════════════════════════════
# 策略引擎输出: 择时决策
# ══════════════════════════════════════════════════════════════════


class ExecutionDetails(BaseModel):
    """
    执行细节 — 告诉 OMS 具体怎么操作

    包含合约选择的完整参数, OMS 可据此直接构造 OrderCreate DTO
    """
    contract_symbol: str | None = Field(
        default=None, description="选中的 OCC 合约代码",
    )
    strike_price: float | None = Field(
        default=None, gt=0, description="行权价",
    )
    target_delta: float | None = Field(
        default=None, description="目标 Delta 值 (通常 0.16)",
    )
    actual_delta: float | None = Field(
        default=None, description="实际选中合约的 Delta",
    )
    dte: int | None = Field(
        default=None, ge=0, description="剩余到期天数",
    )
    limit_price: float | None = Field(
        default=None, ge=0, description="建议挂单限价 (mid_price)",
    )
    expiration: str | None = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="到期日",
    )
    estimated_premium: float | None = Field(
        default=None, ge=0, description="预估收取权利金 (per share)",
    )
    open_interest: int | None = Field(
        default=None, ge=0, description="选中合约的 OI",
    )
    volume: int | None = Field(
        default=None, ge=0, description="选中合约的当日成交量",
    )


class TimingDecision(BaseModel):
    """
    择时决策 — 策略引擎的最终输出

    由 StrategyEntryEngine 或 LifecycleScannerEngine 生成,
    交给 OrderManagerService 执行
    """
    action_type: ActionType = Field(..., description="操作类型")
    target_ticker: str = Field(..., description="标的代码")
    scene_label: str = Field(
        ...,
        description=(
            "触发的场景标识, 如:\n"
            "  开仓: 'Scene A: Oversold', 'Scene D: Range-Bound'\n"
            "  生命周期: 'Take-Profit: 50% Reached', 'Gamma Trap: DTE ≤ 21'"
        ),
    )
    confidence: float = Field(
        default=0.5, ge=0, le=1,
        description="决策置信度 (0~1), 供前端显示和审计",
    )
    execution_details: ExecutionDetails = Field(
        default_factory=ExecutionDetails,
        description="具体执行参数",
    )
    reasoning: str = Field(
        default="",
        description="决策推理过程 (自然语言, 供审计日志和前端展示)",
    )
    timestamp: datetime | None = Field(
        default=None,
        description="决策生成时间 (UTC)",
    )


# ══════════════════════════════════════════════════════════════════
# 持仓快照 (生命周期扫描输入)
# ══════════════════════════════════════════════════════════════════


class PositionSnapshot(BaseModel):
    """
    持仓快照 — 生命周期巡检引擎的输入

    与 ORM Position 模型的区别:
    - Position: SQLAlchemy ORM 对象, 强绑定数据库
    - PositionSnapshot: 纯 DTO, 无 I/O 依赖, 可测试

    初始权利金和当前市价由 PositionService 从 DB + 行情 API 组合填充
    """
    ticker: str = Field(..., description="标的代码")
    contract_symbol: str | None = Field(default=None, description="期权合约代码")
    position_type: str = Field(
        ..., pattern=r"^(short_put|short_call|long_stock|buy_write)$",
        description="持仓类型",
    )
    quantity: int = Field(..., description="持仓数量 (正 = 多, 负 = 空)")
    strike: float | None = Field(default=None, gt=0, description="行权价")
    expiration: str | None = Field(default=None, description="到期日 YYYY-MM-DD")

    # ── 盈亏核心字段 ──
    initial_premium: float = Field(
        ..., ge=0,
        description=(
            "初始收取的权利金 (per share)。"
            "对于 Short Option: 这是卖出时收到的权利金。"
            "止盈判断: (initial_premium - current_cost) / initial_premium ≥ 0.50"
        ),
    )
    current_cost: float = Field(
        ..., ge=0,
        description=(
            "当前买回成本 (per share)。"
            "即当前市场上 Buy-to-Close 的价格 (通常取 ask 价)。"
            "如果 current_cost 很低, 说明时间价值已充分衰减"
        ),
    )
    underlying_price: float = Field(
        ..., gt=0,
        description="标的当前价格 (用于判断 ATM 逼近)",
    )

    @property
    def dte(self) -> int:
        """剩余到期天数"""
        if not self.expiration:
            return 999
        exp = datetime.strptime(self.expiration, "%Y-%m-%d").date()
        return max(0, (exp - date.today()).days)

    @property
    def profit_pct(self) -> float:
        """
        已实现利润比例 (仅适用于 Short Option)

        公式: (初始权利金 - 当前买回成本) / 初始权利金
        示例: 卖出时收 $3.00, 现在买回只需 $1.00 → 利润 66.7%
        达到 50% 即触发止盈信号
        """
        if self.initial_premium <= 0:
            return 0.0
        return round(
            (self.initial_premium - self.current_cost) / self.initial_premium,
            4,
        )

    @property
    def is_atm(self) -> bool:
        """
        是否逼近 ATM (At-The-Money)

        当标的价格距离行权价在 2% 以内时, 视为 ATM 区域
        ATM 期权的 Gamma 最大, DTE 低时风险骤增
        """
        if not self.strike:
            return False
        return abs(self.underlying_price - self.strike) / self.strike < 0.02

    @property
    def is_in_the_money(self) -> bool:
        """
        是否 ITM (In-The-Money, 实值)

        Short Put ITM: 标的价格 < 行权价 (Put 卖方亏损)
        Short Call ITM: 标的价格 > 行权价 (Call 卖方可能被指派)
        """
        if not self.strike:
            return False
        if "put" in self.position_type:
            return self.underlying_price < self.strike
        if "call" in self.position_type:
            return self.underlying_price > self.strike
        return False


# ══════════════════════════════════════════════════════════════════
# 保留原有 Projection / CorporateAction DTOs (向后兼容)
# ══════════════════════════════════════════════════════════════════


class ProjectionRequest(BaseModel):
    """损益推演请求"""
    strategy: str   # covered_call | cash_secured_put
    price: float | None = None
    strike: float
    premium: float
    dte: int
    quantity: int = 100


class ProjectionResponse(BaseModel):
    """损益推演结果"""
    net_cost: float | None = None
    break_even: float
    max_profit: float
    max_loss: float | None = None
    annualized_yield: float


class CorporateAction(BaseModel):
    """公司行动事件 (拆股/除息)"""
    ticker: str
    action_type: str  # split | dividend
    ratio: float | None = None
    ex_date: str | None = None
    amount: float | None = None
