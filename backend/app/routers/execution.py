"""
Execution Router — 组合单 (Combo Orders) 执行接口
"""
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.order import Order, OrderStatus
from app.models.transaction import TransactionLedger, LegType

logger = logging.getLogger("alphatheta.router.execution")
router = APIRouter()


class RollComboRequest(BaseModel):
    """展期组合单请求"""
    old_order_id: str = Field(..., description="旧仓 Order UUID")
    new_strike: float = Field(..., gt=0, description="新行权价")
    new_expiration: str = Field(..., description="新到期日 YYYY-MM-DD")
    net_limit_price: float = Field(..., description="净限价 (credit 为正, debit 为负)")
    quantity: int = Field(1, ge=1, description="合约数量")


@router.post("/roll_combo")
async def roll_combo(req: RollComboRequest):
    """
    展期组合单 — 原子事务:
    1. Buy to Close 旧仓 (标记 CANCELLED)
    2. Sell to Open 新仓 (创建 PENDING)
    3. TransactionLedger 写入双条目
    """
    async with get_async_session() as session:
        async with session.begin():
            # ── 1. 验证旧仓 ──
            old_order = await session.get(Order, uuid.UUID(req.old_order_id))
            if not old_order:
                raise HTTPException(
                    status_code=404,
                    detail=f"旧仓 Order {req.old_order_id} 不存在",
                )

            valid_statuses = [
                OrderStatus.FILLED.value,
                OrderStatus.PARTIAL_FILL.value,
            ]
            if old_order.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"旧仓状态 '{old_order.status}' 不可展期，仅 FILLED/PARTIAL_FILL 可操作",
                )

            # ── 2. Buy to Close — 标记旧仓为 CANCELLED ──
            close_price = req.net_limit_price  # 简化: 用 net limit 作为 close price
            old_order.status = OrderStatus.CANCELLED.value
            old_order.updated_at = datetime.utcnow()

            logger.info(
                f"[Roll] Closing old order {old_order.id} "
                f"({old_order.ticker} {old_order.strike} {old_order.expiration})"
            )

            # ── 3. Sell to Open — 创建新仓 ──
            new_order = Order(
                id=uuid.uuid4(),
                ticker=old_order.ticker,
                action_type=old_order.action_type,
                order_type=old_order.order_type,
                strike=req.new_strike,
                expiration=req.new_expiration,
                quantity=req.quantity,
                limit_price=req.net_limit_price,
                status=OrderStatus.PENDING.value,
                env_mode=old_order.env_mode,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(new_order)

            logger.info(
                f"[Roll] Opening new order {new_order.id} "
                f"({old_order.ticker} {req.new_strike} {req.new_expiration})"
            )

            # ── 4. TransactionLedger 双条目 ──
            multiplier = 100  # 期权合约乘数

            close_leg = TransactionLedger(
                id=uuid.uuid4(),
                order_id=old_order.id,
                ticker=old_order.ticker,
                leg_type=LegType.ROLL_CLOSE,
                quantity=req.quantity,
                price=old_order.filled_price or old_order.limit_price or 0,
                net_amount=-(req.quantity * (old_order.filled_price or old_order.limit_price or 0) * multiplier),
                created_at=datetime.utcnow(),
            )

            open_leg = TransactionLedger(
                id=uuid.uuid4(),
                order_id=new_order.id,
                ticker=old_order.ticker,
                leg_type=LegType.ROLL_OPEN,
                quantity=req.quantity,
                price=req.net_limit_price,
                net_amount=req.quantity * req.net_limit_price * multiplier,
                created_at=datetime.utcnow(),
            )

            session.add(close_leg)
            session.add(open_leg)

            logger.info(
                f"[Roll] Ledger: close=${close_leg.net_amount:.2f}, "
                f"open=${open_leg.net_amount:.2f}, "
                f"net=${close_leg.net_amount + open_leg.net_amount:.2f}"
            )

    # ── 5. 返回结果 ──
    net_credit = open_leg.net_amount + close_leg.net_amount
    return {
        "status": "success",
        "old_order": {
            "id": str(old_order.id),
            "ticker": old_order.ticker,
            "strike": old_order.strike,
            "expiration": old_order.expiration,
            "new_status": "cancelled",
        },
        "new_order": {
            "id": str(new_order.id),
            "ticker": new_order.ticker,
            "strike": req.new_strike,
            "expiration": req.new_expiration,
            "status": "pending",
        },
        "ledger": {
            "close_amount": close_leg.net_amount,
            "open_amount": open_leg.net_amount,
            "net_credit": net_credit,
        },
        "message": f"展期完成: Net {'Credit' if net_credit > 0 else 'Debit'} ${abs(net_credit):.2f}",
    }
