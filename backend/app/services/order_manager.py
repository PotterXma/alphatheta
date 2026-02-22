"""
订单生命周期管理服务 — 状态机 + 事务原子性 + 幂等

核心设计:
┌──────────────────────────────────────────────────────────────────┐
│ FSM (有限状态机)                                                │
│   Draft → Pending → Filled (终态)                               │
│                  → PartialFill → Filled (终态)                  │
│                  → Rejected (终态)                               │
│                  → Cancelled (终态)                              │
│   Draft → Cancelled (终态)                                      │
│   终态 (Filled | Rejected | Cancelled) → 任何状态 = 异常        │
├──────────────────────────────────────────────────────────────────┤
│ 事务原子性 (ACID)                                               │
│   订单 Fill → 必须在同一个 DB 事务中同时更新:                    │
│   1. orders 表 (status → Filled, filled_price, filled_at)       │
│   2. positions 表 (quantity ± fill_qty, avg_cost 加权均价)       │
│   任一步骤失败 → 整个事务 ROLLBACK                               │
├──────────────────────────────────────────────────────────────────┤
│ 幂等保障                                                        │
│   同 idempotency_key 的重复请求 → 返回已有订单，不重复提交       │
│   依赖 orders.idempotency_key UNIQUE 约束                       │
└──────────────────────────────────────────────────────────────────┘
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.broker_base import BrokerAdapter, BrokerOrderResponse
from app.config import get_settings
from app.models.order import InvalidStateTransition, Order, OrderStatus
from app.models.position import Position
from app.schemas.order import OrderCreate, RollRequest, RollResponse

logger = logging.getLogger("alphatheta.order_manager")


# ── 执行报告数据结构 ──

@dataclass
class ExecutionReport:
    """
    券商执行回报 — 用于 handle_broker_execution_report

    来源:
    1. 券商 WebSocket 推送的实时成交通知
    2. 对账守护进程 (reconciliation) 轮询发现的状态变更
    3. 券商 HTTP 回调 (Webhook)
    """
    broker_order_id: str
    status: str                     # "filled", "partial_fill", "cancelled", "rejected"
    filled_price: float | None = None
    filled_quantity: int | None = None
    rejection_reason: str | None = None


class OrderManagerService:
    """
    OMS 核心服务 — 订单全生命周期管理

    职责:
    1. 创建订单 (Draft) → 提交到券商 (Pending)
    2. 处理券商异步执行回报 → FSM 状态流转
    3. 成交 (Fill) 时原子更新持仓 (同一 DB 事务)
    4. 取消订单 → 通知券商 + 本地状态更新

    事务管理策略:
    - 本类不自行管理事务生命周期 (不调用 session.commit)
    - 依赖调用方 (路由层) 通过 `async with session.begin():` 控制事务边界
    - 但 handle_broker_execution_report 是例外 — 它自行开启嵌套事务
      确保 order + position 更新的原子性
    """

    def __init__(self, db: AsyncSession, broker: BrokerAdapter):
        self.db = db
        self.broker = broker

    # ══════════════════════════════════════════════════════════════
    # 1. 创建 + 提交订单
    # ══════════════════════════════════════════════════════════════

    async def submit_order(self, order_create_dto: OrderCreate) -> Order:
        """
        创建订单并提交到券商

        流程:
        1. 在 DB 创建 Draft 订单
        2. FSM: Draft → Pending
        3. 调用 BrokerAdapter.submit_order()
        4. 根据券商同步响应:
           - "filled"   → Pending → Filled + 原子更新持仓
           - "pending"  → 保持 Pending (等待异步回报)
           - "rejected" → Pending → Rejected

        幂等: idempotency_key 相同的请求会查到已有订单直接返回
        """
        settings = get_settings()
        idem_key = str(order_create_dto.idempotency_key)

        # ── 幂等检查: 同 Key 订单已存在 → 直接返回 ──
        existing = await self._find_by_idempotency_key(idem_key)
        if existing is not None:
            logger.info(f"幂等命中: order={existing.id} key={idem_key}")
            return existing

        # ── Step 1: 创建 Draft 订单 ──
        order = Order(
            ticker=order_create_dto.ticker,
            action_type=order_create_dto.action_type,
            order_type=order_create_dto.order_type.value,
            strike=order_create_dto.strike,
            expiration=order_create_dto.expiration,
            quantity=order_create_dto.quantity,
            limit_price=order_create_dto.limit_price,
            idempotency_key=idem_key,
            status=OrderStatus.DRAFT,
            env_mode=settings.env_mode.value,
        )
        self.db.add(order)
        await self.db.flush()  # 获取 order.id
        logger.info(
            f"📝 Order created: id={order.id} "
            f"ticker={order.ticker} action={order.action_type} qty={order.quantity}"
        )

        # ── Step 2: Draft → Pending ──
        order.transition(OrderStatus.PENDING)

        # ── Step 3: 调用券商 API ──
        try:
            broker_resp: BrokerOrderResponse = await self.broker.submit_order(
                ticker=order.ticker,
                action=order.action_type,
                quantity=order.quantity,
                order_type=order.order_type,
                limit_price=order.limit_price,
                strike=order.strike,
                expiration=order.expiration,
                idempotency_key=idem_key,
            )
            order.broker_order_id = broker_resp.broker_order_id
        except Exception as e:
            # 券商通信失败 → 直接拒绝
            logger.error(f"❌ Broker submit failed: {order.id} — {e}")
            order.transition(OrderStatus.REJECTED)
            order.rejection_reason = f"Broker communication error: {e}"
            await self.db.flush()
            return order

        # ── Step 4: 根据券商同步响应更新状态 ──
        if broker_resp.status == "filled":
            # 同步成交 (Paper 模式或立即成交的市价单)
            await self._apply_fill(
                order=order,
                filled_price=broker_resp.filled_price,
                filled_quantity=broker_resp.filled_quantity,
            )
        elif broker_resp.status == "rejected":
            order.transition(OrderStatus.REJECTED)
            order.rejection_reason = broker_resp.rejection_reason or "Broker rejected"
            logger.warning(f"🚫 Order rejected: {order.id} — {order.rejection_reason}")
        else:
            # "pending" — 保持 Pending，等待异步回报
            logger.info(f"⏳ Order pending at broker: {order.id} broker_id={order.broker_order_id}")

        await self.db.flush()
        return order

    # ══════════════════════════════════════════════════════════════
    # 2. 处理券商异步执行回报
    # ══════════════════════════════════════════════════════════════

    async def handle_broker_execution_report(
        self,
        order_id: uuid.UUID,
        execution_report: ExecutionReport,
    ) -> Order:
        """
        处理券商异步执行回报 — FSM 校验 + 事务原子性

        调用场景:
        1. WebSocket 推送成交通知
        2. 对账守护进程发现状态不一致
        3. 定时轮询 broker.get_order_status()

        事务保障:
        - 使用 session.begin_nested() (SAVEPOINT) 确保原子性
        - 如果 order 更新成功但 position 更新失败 → 回滚到 SAVEPOINT
        - 不影响外层事务

        FSM 校验:
        - 终态 (Filled/Rejected/Cancelled) 收到再次流转 → 抛 InvalidStateTransition
        - 这是防止重复处理的关键
        """
        order = await self.db.get(Order, order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")

        # ── FSM 终态保护 ──
        # 如果订单已处于终态，任何新的状态变更都是非法的
        # 这里会抛出 InvalidStateTransition，由路由层捕获返回 409
        target_status = self._map_report_to_status(execution_report.status)

        # 使用 SAVEPOINT 嵌套事务 — 确保 order + position 原子更新
        async with self.db.begin_nested():
            # transition() 内部会校验 FSM 合法性
            # 终态 → 任何状态 = InvalidStateTransition 异常 → SAVEPOINT 回滚
            order.transition(target_status)

            if target_status == OrderStatus.FILLED:
                await self._apply_fill(
                    order=order,
                    filled_price=execution_report.filled_price,
                    filled_quantity=execution_report.filled_quantity,
                )
            elif target_status == OrderStatus.PARTIAL_FILL:
                order.filled_price = execution_report.filled_price
                order.filled_quantity = execution_report.filled_quantity
                logger.info(
                    f"📊 Partial fill: {order.id} "
                    f"qty={execution_report.filled_quantity}/{order.quantity}"
                )
            elif target_status == OrderStatus.REJECTED:
                order.rejection_reason = execution_report.rejection_reason or "Broker rejected async"
                logger.warning(f"🚫 Async rejection: {order.id}")
            elif target_status == OrderStatus.CANCELLED:
                logger.info(f"🔕 Order cancelled by broker: {order.id}")

            await self.db.flush()

        logger.info(
            f"✅ Execution report processed: order={order.id} "
            f"status={order.status.value}"
        )
        return order

    # ══════════════════════════════════════════════════════════════
    # 3. 取消订单
    # ══════════════════════════════════════════════════════════════

    async def cancel_order(self, order_id: uuid.UUID) -> Order:
        """
        取消订单 — 通知券商 + 本地 FSM 流转

        如果订单已提交到券商 (有 broker_order_id):
        1. 先通知券商取消
        2. 再本地 FSM 流转
        3. 券商取消失败 → 不影响本地标记 (以本地为准，对账修复)
        """
        order = await self.db.get(Order, order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")

        # 通知券商取消 (尽力而为，异常不阻塞本地状态)
        if order.broker_order_id:
            try:
                await self.broker.cancel_order(order.broker_order_id)
            except Exception as e:
                logger.warning(
                    f"券商取消失败 (将由对账修复): {order.id} — {e}"
                )

        # FSM: Draft/Pending/PartialFill → Cancelled
        # 如果已经是终态，transition() 会抛 InvalidStateTransition
        order.transition(OrderStatus.CANCELLED)
        await self.db.flush()

        logger.info(f"🔕 Order cancelled: {order.id}")
        return order

    # ══════════════════════════════════════════════════════════════
    # 4. 查询
    # ══════════════════════════════════════════════════════════════

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        """查询单个订单"""
        return await self.db.get(Order, order_id)

    async def list_orders(
        self,
        env_mode: str | None = None,
        status: OrderStatus | None = None,
        limit: int = 50,
    ) -> list[Order]:
        """查询订单列表 — 支持按环境和状态筛选"""
        stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
        if env_mode:
            stmt = stmt.where(Order.env_mode == env_mode)
        if status:
            stmt = stmt.where(Order.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_positions(self, env_mode: str | None = None) -> list[Position]:
        """查询持仓列表"""
        stmt = select(Position)
        if env_mode:
            stmt = stmt.where(Position.env_mode == env_mode)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════
    # 5. 展期 (Roll)
    # ══════════════════════════════════════════════════════════════

    def calculate_roll(
        self, req: RollRequest, current_strike: float, current_exp: str
    ) -> RollResponse:
        """
        展期计算: Roll Up / Down / Out

        Roll Up:  Strike × 1.05 (上移 5%)
        Roll Down: Strike × 0.90 (下移 10%)
        Roll Out:  Strike 不变, + 30 天
        """
        from datetime import timedelta

        if req.roll_type == "up":
            new_strike = round(current_strike * 1.05, 2)
        elif req.roll_type == "down":
            new_strike = round(current_strike * 0.90, 2)
        else:  # out
            new_strike = current_strike

        exp_date = datetime.strptime(current_exp, "%Y-%m-%d") if current_exp else datetime.now()
        new_exp = (exp_date + timedelta(days=30)).strftime("%Y-%m-%d")

        return RollResponse(
            original_strike=current_strike,
            new_strike=new_strike,
            new_expiration=new_exp,
            estimated_credit_or_debit=-0.50,  # TODO: 由 Tradier API 查询实际价差
            roll_type=req.roll_type,
        )

    # ══════════════════════════════════════════════════════════════
    # Private — 内部辅助方法
    # ══════════════════════════════════════════════════════════════

    async def _apply_fill(
        self,
        order: Order,
        filled_price: float | None,
        filled_quantity: int | None,
    ) -> None:
        """
        应用成交 — 更新订单 + 持仓 (同一事务)

        持仓更新逻辑:
        - BUY / Buy Stock / Buy-Write: 增加持仓 (加权平均成本)
        - SELL / Sell Put / Sell Call: 减少持仓 (减至 0 时不删除)

        加权均价公式:
        new_avg = (old_avg × old_qty + fill_price × fill_qty) / new_total_qty

        注意: 此方法必须在事务上下文内调用
        """
        fill_qty = filled_quantity or order.quantity
        fill_price = filled_price or order.limit_price or 0.0

        # 更新订单成交信息
        order.transition(OrderStatus.FILLED)
        order.filled_price = fill_price
        order.filled_quantity = fill_qty
        order.filled_at = datetime.now(timezone.utc)

        # ── 持仓更新 ──
        result = await self.db.execute(
            select(Position).where(
                Position.ticker == order.ticker,
                Position.env_mode == order.env_mode,
            )
        )
        pos = result.scalar_one_or_none()

        # 判断方向: action_type 包含 "Sell" 则为卖出 (减仓)
        is_sell = "sell" in order.action_type.lower()

        if pos is None:
            # 首次建仓
            pos = Position(
                ticker=order.ticker,
                quantity=-fill_qty if is_sell else fill_qty,
                avg_cost_basis=fill_price,
                env_mode=order.env_mode,
            )
            self.db.add(pos)
            logger.info(
                f"📦 New position: {order.ticker} "
                f"qty={'−' if is_sell else '+'}{fill_qty} @ ${fill_price:.2f}"
            )
        else:
            if is_sell:
                # 卖出 → 减仓 (avg_cost 不变)
                pos.quantity -= fill_qty
            else:
                # 买入 → 加仓 (加权平均成本)
                old_total = pos.avg_cost_basis * abs(pos.quantity)
                new_total = old_total + fill_price * fill_qty
                pos.quantity += fill_qty
                if pos.quantity != 0:
                    pos.avg_cost_basis = new_total / abs(pos.quantity)
            logger.info(
                f"📦 Position updated: {order.ticker} "
                f"qty={pos.quantity} avg=${pos.avg_cost_basis:.2f}"
            )

        await self.db.flush()
        logger.info(
            f"✅ Order filled: {order.id} "
            f"price=${fill_price:.2f} qty={fill_qty}"
        )

    async def _find_by_idempotency_key(self, key: str) -> Order | None:
        """通过幂等键查找已有订单"""
        result = await self.db.execute(
            select(Order).where(Order.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _map_report_to_status(broker_status: str) -> OrderStatus:
        """
        将券商报告状态映射到内部 FSM 状态

        券商可能返回的状态字符串不统一 (Tradier vs Paper)
        这里统一映射
        """
        mapping = {
            "filled": OrderStatus.FILLED,
            "partial_fill": OrderStatus.PARTIAL_FILL,
            "partially_filled": OrderStatus.PARTIAL_FILL,
            "rejected": OrderStatus.REJECTED,
            "cancelled": OrderStatus.CANCELLED,
            "canceled": OrderStatus.CANCELLED,  # 美式拼写
            "expired": OrderStatus.CANCELLED,   # 到期 = 取消
        }
        status = mapping.get(broker_status.lower())
        if status is None:
            raise ValueError(
                f"Unknown broker status: '{broker_status}'. "
                f"Expected: {list(mapping.keys())}"
            )
        return status
