"""
风控引擎数据契约 — CRO 评估的输入与输出

设计要点:
1. TradeProposal 引用 OrderCreate 作为嵌套对象，避免字段重复
2. 所有 margin / portfolio 字段带 ge=0 约束
3. est_tax_drag 默认 0.30 (美国短期资本利得税率)
4. RiskAssessment 输出携带完整的拒绝原因链、执行方案和情景剧本
"""

from pydantic import BaseModel, Field

from app.schemas.order import OrderCreate


class TradeProposal(BaseModel):
    """
    风控评估提案 — 前端或策略引擎提交给 CRO 的完整交易提案

    包含订单本身 + 组合层面的风险参数
    """

    order: OrderCreate = Field(
        ...,
        description="待评估的订单详情 (包含 idempotency_key)",
    )
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="标的代码",
    )

    # ── 市场层面参数 ──
    bid: float = Field(
        ..., ge=0,
        description="当前 Bid 价格 (最优买价)",
    )
    ask: float = Field(
        ..., ge=0,
        description="当前 Ask 价格 (最优卖价)",
    )
    delta: float = Field(
        default=0.0,
        ge=-1.0, le=1.0,
        description="期权 Delta 值，-1.0 ~ 1.0",
    )
    gamma: float = Field(
        default=0.0,
        ge=0.0,
        description="期权 Gamma 值，≥ 0",
    )
    dte: int = Field(
        default=30,
        ge=0, le=365,
        description="距到期天数 (Days To Expiration)",
    )

    # ── 组合层面参数 ──
    estimated_margin_impact: float = Field(
        default=0.0,
        ge=0.0,
        description="预计 Margin 占用增量 ($)",
    )
    current_portfolio_value: float = Field(
        default=0.0,
        ge=0.0,
        description="当前组合总市值 ($)",
    )
    projected_margin_util: float = Field(
        default=0.0,
        ge=0.0, le=100.0,
        description="预计 Margin 利用率 (%)",
    )

    # ── 风险标志 ──
    days_to_ex_dividend: int = Field(
        default=999,
        ge=0,
        description="距除权日天数 (999 = 无近期除权)",
    )
    is_itm: bool = Field(
        default=False,
        description="是否为实值期权 (In-The-Money)",
    )
    is_wash_sale_risk: bool = Field(
        default=False,
        description="是否存在 Wash Sale 风险 (30天内同标的亏损卖出)",
    )
    est_tax_drag: float = Field(
        default=0.30,
        ge=0.0, le=1.0,
        description="预估税拖系数 (0 = 免税, 0.30 = 30% 短期资本利得)",
    )

    # ── 市场波动 ──
    hv_30d: float | None = Field(
        default=None,
        ge=0.0,
        description="30日历史波动率 (%)",
    )
    iv_rank: float | None = Field(
        default=None,
        ge=0.0, le=100.0,
        description="隐含波动率百分位 (0-100)",
    )


class ExecutionPlan(BaseModel):
    """风控通过后的执行方案"""
    recommended_order_type: str = Field(
        default="Limit_Price_Chaser",
        description="建议订单类型",
    )
    starting_limit_price: float = Field(
        ..., ge=0,
        description="起始限价",
    )
    floor_limit_price: float = Field(
        ..., ge=0,
        description="底线限价 (追价最低价)",
    )
    gross_annualized_yield_est: float = Field(
        ...,
        description="毛年化收益率估算 (%)",
    )
    net_annualized_yield_after_tax: float = Field(
        ...,
        description="税后净年化收益率 (%)",
    )


class ScenarioPlaybook(BaseModel):
    """情景剧本 — 预设行情走势下的应对策略"""
    title: str = Field(..., description="剧本标题，如 📈 Bullish Surge (+15%)")
    scenario: str = Field(..., description="行情描述")
    action: str = Field(..., description="应对策略")
    target_price: float | None = Field(default=None, ge=0, description="目标价格")


class RiskAssessment(BaseModel):
    """
    CRO 风控评估结果

    is_approved=True → 携带 execution_plan + scenario_playbooks
    is_approved=False → 携带 rejection_reason
    """
    is_approved: bool = Field(
        ...,
        description="风控是否通过",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="拒绝原因 (仅 is_approved=False 时有值)",
    )
    rejection_rule: str | None = Field(
        default=None,
        description="触发的 Kill Switch 规则编号，如 Rule 3·Spread",
    )
    execution_plan: ExecutionPlan | None = Field(
        default=None,
        description="执行方案 (仅通过时有值)",
    )
    scenario_playbooks: list[ScenarioPlaybook] = Field(
        default_factory=list,
        description="情景剧本列表",
    )
    ui_rationale: list[str] = Field(
        default_factory=list,
        description="UI 展示用的人类可读理由列表",
    )


# ══════════════════════════════════════════════════════════════════
# 动态风控参数 DTO — ATR/IV 自适应防线 (新增)
# ══════════════════════════════════════════════════════════════════

class RiskScenarioDTO(BaseModel):
    """单条风控情景 — 前端渲染最小单元"""
    scenario_name: str = Field(..., description="情景名称 (含 emoji)")
    trigger_condition: str = Field(..., description="触发条件文本")
    action_plan: str = Field(..., description="应对动作")
    tag_type: str = Field(
        ...,
        pattern=r"^(danger|warning|info|success)$",
        description="风控级别 → 前端颜色映射",
    )
    threshold_price: float | None = Field(None, description="触发价格锚点")
    priority: int = Field(5, ge=1, le=10, description="优先级 (1=最高)")


class DynamicRiskParamsDTO(BaseModel):
    """动态风控参数集合 — /dashboard/sync 返回"""
    ticker: str
    strategy_type: str
    current_price: float
    implied_move_1sigma: float = Field(..., description="1σ 隐含移动")
    implied_move_2sigma: float = Field(..., description="2σ 隐含移动")
    atr_stop_loss: float = Field(..., description="2×ATR 止损价位")
    upside_1sigma: float = Field(..., description="1σ 上行边界")
    downside_1sigma: float = Field(..., description="1σ 下行边界")
    scenarios: list[RiskScenarioDTO] = Field(default_factory=list)
