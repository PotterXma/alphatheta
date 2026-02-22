"""对账守护进程 — 独立于发单链路，定期比对券商 vs 本地状态"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.broker_base import BrokerAdapter
from app.models.order import Order, OrderStatus

logger = logging.getLogger("alphatheta.reconciliation")


class ReconciliationDaemon:
    """
    对账引擎 — 每 60s 执行:
    1. 拉取券商真实 open orders / positions
    2. 对比本地 Pending 订单
    3. 修复不一致并触发 CRITICAL 审计日志
    """

    INTERVAL_SECONDS = 60

    def __init__(self, db_factory, broker: BrokerAdapter, admin_service=None):
        self.db_factory = db_factory
        self.broker = broker
        self.admin = admin_service
        self._running = False

    async def start(self):
        """启动对账循环"""
        self._running = True
        logger.info("Reconciliation daemon started")
        while self._running:
            try:
                await self._reconcile()
            except Exception as e:
                logger.error(f"Reconciliation error: {e}")
            await asyncio.sleep(self.INTERVAL_SECONDS)

    async def stop(self):
        self._running = False
        logger.info("Reconciliation daemon stopped")

    async def _reconcile(self):
        """单次对账"""
        async with self.db_factory() as db:
            # 获取本地 Pending 订单
            result = await db.execute(
                select(Order).where(Order.status == OrderStatus.PENDING)
            )
            local_pending = {o.broker_order_id: o for o in result.scalars().all() if o.broker_order_id}

            if not local_pending:
                return

            # 逐一检查券商状态
            mismatches = 0
            for broker_id, order in local_pending.items():
                try:
                    broker_status = await self.broker.get_order_status(broker_id)

                    if broker_status.status == "filled" and order.status == OrderStatus.PENDING:
                        # 漏填: 本地未更新
                        order.transition(OrderStatus.FILLED)
                        order.filled_price = broker_status.filled_price
                        order.filled_quantity = broker_status.filled_quantity
                        mismatches += 1
                        logger.critical(f"RECONCILIATION: Missed fill detected for {broker_id}")

                    elif broker_status.status == "unknown":
                        # 幽灵订单: 券商无记录
                        order.transition(OrderStatus.REJECTED)
                        order.rejection_reason = "broker_not_found_on_reconciliation"
                        mismatches += 1
                        logger.critical(f"RECONCILIATION: Phantom order detected {broker_id}")

                except Exception as e:
                    logger.error(f"Reconciliation check failed for {broker_id}: {e}")

            if mismatches > 0:
                await db.commit()
                logger.warning(f"Reconciliation found {mismatches} mismatches")
