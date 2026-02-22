"""Order Management API Router"""

import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_broker_adapter, get_db
from app.schemas.order import OrderCreate, OrderResponse, PositionResponse, RollRequest, RollResponse
from app.services.order_manager import OrderManagerService

router = APIRouter()


@router.post("", response_model=OrderResponse)
async def create_order(
    req: OrderCreate,
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_adapter),
):
    """创建 Draft 订单"""
    mgr = OrderManagerService(db, broker)
    order = await mgr.submit_order(req)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/submit", response_model=OrderResponse)
async def submit_order(
    order_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_adapter),
):
    """提交订单到券商 (需要 Idempotency-Key header)"""
    mgr = OrderManagerService(db, broker)
    order = await mgr.submit_order(req)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    broker=Depends(get_broker_adapter),
):
    """取消订单"""
    mgr = OrderManagerService(db, broker)
    order = await mgr.cancel_order(order_id)
    return OrderResponse.model_validate(order)


@router.post("/roll", response_model=RollResponse)
async def roll_position(req: RollRequest):
    """展期计算 (Roll Up/Down/Out)"""
    # TODO: 从持仓加载 current_strike 和 expiration
    from app.services.order_manager import OrderManagerService
    mgr = OrderManagerService.__new__(OrderManagerService)
    return mgr.calculate_roll(req, current_strike=525.0, current_exp="2025-04-18")


@router.get("", response_model=list[OrderResponse])
async def list_orders(db: AsyncSession = Depends(get_db)):
    """查询订单列表"""
    from sqlalchemy import select
    from app.models.order import Order
    result = await db.execute(select(Order).order_by(Order.created_at.desc()).limit(50))
    return [OrderResponse.model_validate(o) for o in result.scalars().all()]


@router.get("/positions", response_model=list[PositionResponse])
async def list_positions(db: AsyncSession = Depends(get_db)):
    """查询当前持仓"""
    from sqlalchemy import select
    from app.models.position import Position
    result = await db.execute(select(Position))
    return [PositionResponse.model_validate(p) for p in result.scalars().all()]
