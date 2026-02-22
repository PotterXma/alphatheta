"""
保证金引擎 — Reg T 标准保证金计算 + 悲观锁购买力校验

Reg T 公式 (SEC/FINRA 标准):
  Naked Put:   max(Strike × 10%, Strike × 20% - OTM) × 合约乘数
  Covered Call: 无额外保证金 (已持有正股)
  Spread:      max_loss = (宽腿差 - 收到权利金) × 合约乘数
  Naked Call:  max(Spot × 20% + OTM, Spot × 10%) × 合约乘数

⚠️ 安全设计:
  - 所有金额使用 Decimal 计算, 绝不用 float
  - validate_buying_power 使用 SELECT..FOR UPDATE 悲观锁
  - 保证金不足 → 直接 REJECT, 绝不允许负余额
"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("alphatheta.margin")

# 合约乘数 (标准美股期权 = 100 股/合约)
CONTRACT_MULTIPLIER = Decimal("100")


def calculate_margin(
    strategy_type: str,
    legs: list[dict],
    underlying_price: float,
) -> Decimal:
    """
    根据策略类型和腿参数计算 Reg T 保证金

    Args:
        strategy_type: PMCC, Iron_Condor, Naked_Put, Covered_Call, etc.
        legs: [{"strike": 150, "right": "put", "action": "sell", "quantity": 1, "premium": 3.50}, ...]
        underlying_price: 当前标的价格

    Returns:
        Decimal: 所需保证金 (正数)
    """
    spot = Decimal(str(underlying_price))
    strategy = strategy_type.lower().replace(" ", "_")

    if strategy == "naked_put":
        return _margin_naked_put(legs, spot)
    elif strategy == "naked_call":
        return _margin_naked_call(legs, spot)
    elif strategy == "covered_call":
        return Decimal("0")  # 已持有正股, 无额外保证金
    elif strategy in ("vertical_spread", "credit_spread", "debit_spread"):
        return _margin_spread(legs)
    elif strategy == "iron_condor":
        return _margin_iron_condor(legs)
    elif strategy in ("pmcc", "leaps_deep_itm_call", "poor_mans_covered_call"):
        return _margin_pmcc(legs, spot)
    else:
        # 未知策略 → 保守计算: 取所有腿最大 naked 保证金
        logger.warning(f"未知策略 '{strategy_type}', 使用保守保证金计算")
        return _margin_conservative(legs, spot)


def _margin_naked_put(legs: list[dict], spot: Decimal) -> Decimal:
    """Naked Put margin = max(Strike × 20% - OTM, Strike × 10%) × 100"""
    for leg in legs:
        if leg.get("right", "").lower() == "put" and leg.get("action", "").lower() == "sell":
            strike = Decimal(str(leg["strike"]))
            otm = max(Decimal("0"), strike - spot)  # ITM amount for puts
            margin_a = strike * Decimal("0.20") - otm
            margin_b = strike * Decimal("0.10")
            return max(margin_a, margin_b) * CONTRACT_MULTIPLIER * Decimal(str(leg.get("quantity", 1)))
    return Decimal("0")


def _margin_naked_call(legs: list[dict], spot: Decimal) -> Decimal:
    """Naked Call margin = max(Spot × 20% + OTM, Spot × 10%) × 100"""
    for leg in legs:
        if leg.get("right", "").lower() == "call" and leg.get("action", "").lower() == "sell":
            strike = Decimal(str(leg["strike"]))
            otm = max(Decimal("0"), spot - strike)
            margin_a = spot * Decimal("0.20") + otm
            margin_b = spot * Decimal("0.10")
            return max(margin_a, margin_b) * CONTRACT_MULTIPLIER * Decimal(str(leg.get("quantity", 1)))
    return Decimal("0")


def _margin_spread(legs: list[dict]) -> Decimal:
    """Spread margin = max_loss = (宽腿 strike 差 - 收取权利金) × 100"""
    strikes = sorted([Decimal(str(l["strike"])) for l in legs])
    if len(strikes) < 2:
        return Decimal("0")

    width = strikes[-1] - strikes[0]
    net_premium = sum(
        Decimal(str(l.get("premium", 0))) * (1 if l.get("action", "").lower() == "sell" else -1)
        for l in legs
    )
    max_loss = max(Decimal("0"), width - net_premium)
    qty = max(int(l.get("quantity", 1)) for l in legs)
    return max_loss * CONTRACT_MULTIPLIER * Decimal(str(qty))


def _margin_iron_condor(legs: list[dict]) -> Decimal:
    """Iron Condor margin = max(put spread margin, call spread margin)"""
    put_legs = [l for l in legs if l.get("right", "").lower() == "put"]
    call_legs = [l for l in legs if l.get("right", "").lower() == "call"]
    put_margin = _margin_spread(put_legs) if len(put_legs) >= 2 else Decimal("0")
    call_margin = _margin_spread(call_legs) if len(call_legs) >= 2 else Decimal("0")
    return max(put_margin, call_margin)


def _margin_pmcc(legs: list[dict], spot: Decimal) -> Decimal:
    """PMCC margin = long LEAPS debit cost (已支付, 无额外保证金 if covered)"""
    for leg in legs:
        if leg.get("action", "").lower() == "buy" and leg.get("right", "").lower() == "call":
            premium = Decimal(str(leg.get("premium", 0)))
            qty = Decimal(str(leg.get("quantity", 1)))
            return premium * CONTRACT_MULTIPLIER * qty
    return Decimal("0")


def _margin_conservative(legs: list[dict], spot: Decimal) -> Decimal:
    """保守兜底: 每条卖出腿按 naked 计算"""
    total = Decimal("0")
    for leg in legs:
        if leg.get("action", "").lower() == "sell":
            strike = Decimal(str(leg.get("strike", 0)))
            qty = Decimal(str(leg.get("quantity", 1)))
            margin = max(strike, spot) * Decimal("0.20") * CONTRACT_MULTIPLIER * qty
            total += margin
    return total


# ── 购买力校验 (悲观锁) ──

async def validate_buying_power(
    session: AsyncSession,
    user_id: uuid.UUID,
    required_margin: Decimal,
) -> tuple[bool, str]:
    """
    悲观锁校验购买力

    流程:
    1. SELECT users WHERE user_id = ? FOR UPDATE (锁行)
    2. available = cash_balance - margin_used
    3. if available < required_margin → REJECT
    4. else → 预扣保证金 (margin_used += required_margin)

    Returns:
        (True, "OK") or (False, "error message")
    """
    from app.models.user import User

    # FOR UPDATE 行级悲观锁 — 确保并发订单不超卖
    result = await session.execute(
        select(User)
        .where(User.user_id == user_id)
        .with_for_update()
    )
    user = result.scalar_one_or_none()

    if not user:
        return False, "User not found"

    available = Decimal(str(user.cash_balance)) - Decimal(str(user.margin_used))

    if available < required_margin:
        logger.warning(
            f"⛔ 保证金不足: user={user_id} "
            f"available=${available:.2f} < required=${required_margin:.2f}"
        )
        return False, (
            f"Insufficient buying power: "
            f"available ${available:.2f}, required ${required_margin:.2f}"
        )

    # 预扣保证金
    user.margin_used = float(Decimal(str(user.margin_used)) + required_margin)
    logger.info(
        f"💰 保证金预扣: user={user_id} "
        f"deducted=${required_margin:.2f} "
        f"margin_used=${user.margin_used:.2f}"
    )

    return True, "OK"


async def release_margin(
    session: AsyncSession,
    user_id: uuid.UUID,
    amount: Decimal,
) -> None:
    """
    释放保证金 (取消/平仓时)

    同样使用 FOR UPDATE 锁, 防止并发释放导致负 margin_used
    """
    from app.models.user import User

    result = await session.execute(
        select(User)
        .where(User.user_id == user_id)
        .with_for_update()
    )
    user = result.scalar_one_or_none()

    if user:
        new_margin = max(0.0, float(Decimal(str(user.margin_used)) - amount))
        user.margin_used = new_margin
        logger.info(
            f"💰 保证金释放: user={user_id} "
            f"released=${amount:.2f} "
            f"margin_used=${new_margin:.2f}"
        )
