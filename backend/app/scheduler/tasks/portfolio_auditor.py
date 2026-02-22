"""
任务二: 生命周期巡检与对账守护 (Portfolio Auditor)

执行频率: 每 30 分钟
职责: 持仓防御 + 券商对账

两大子任务:
┌─────────────────────────────────────────────────────────────┐
│ 子任务 A: Lifecycle Scan (持仓防御)                          │
│   扫描所有期权空头 → 触发止盈/展期信号 → 自动执行            │
│   - 50% Take-Profit → BUY_TO_CLOSE                         │
│   - DTE ≤ 21 Gamma Trap → ROLL_OUT                         │
│   - Deep ITM → ROLL_OUT                                    │
├─────────────────────────────────────────────────────────────┤
│ 子任务 B: Reconciliation (独立对账)                          │
│   拉取券商真实持仓 vs 本地 DB 持仓                           │
│   发现 MISMATCH → CRITICAL 级别 Audit Log 告警              │
│   这是最后一道安全网 — 确保本地状态不会与实际持仓脱锚        │
└─────────────────────────────────────────────────────────────┘

安全机制:
  - 全局 try-except: 单次失败不击溃调度器
  - 独立 DB session: 每次执行创建全新 session
  - 子任务隔离: lifecycle scan 失败不影响 reconciliation
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db.session import get_async_session
from app.models.position import Position
from app.schemas.strategy import ActionType, PositionSnapshot

logger = logging.getLogger("alphatheta.scheduler.portfolio_auditor")


async def run_portfolio_auditor() -> None:
    """
    生命周期巡检 + 对账 — 每 30 分钟由 APScheduler 触发

    两个子任务独立执行, 互不影响:
    1. Lifecycle Scan — 需要开市时段 (休市时 option 价格不更新)
    2. Reconciliation — 任何时段都可以执行 (对账越频繁越安全)
    """
    try:
        logger.info("🔍 Portfolio auditor starting...")
        settings = get_settings()

        # ── 子任务 A: 生命周期巡检 ──
        try:
            await _run_lifecycle_scan(settings)
        except Exception as e:
            logger.exception(f"❌ Lifecycle scan failed: {e}")

        # ── 子任务 B: 券商对账 ──
        try:
            await _run_reconciliation(settings)
        except Exception as e:
            logger.exception(f"❌ Reconciliation failed: {e}")

        logger.info("✅ Portfolio auditor completed")

    except Exception as e:
        # 最外层兜底 — 理论上不应该到这里
        logger.exception(f"❌ Portfolio auditor critical failure: {e}")


# ══════════════════════════════════════════════════════════════
# 子任务 A: 生命周期巡检
# ══════════════════════════════════════════════════════════════


async def _run_lifecycle_scan(settings) -> None:
    """
    扫描期权空头持仓, 触发止盈/展期

    流程:
    1. 从 DB 读取所有 Short Option 持仓
    2. 从券商拉取当前市价 → 构造 PositionSnapshot
    3. 调用 scan_portfolio_lifecycle() → 获取信号列表
    4. 逐个执行: BUY_TO_CLOSE / ROLL_OUT
    """
    async with get_async_session() as session:
        # ── 读取期权空头持仓 ──
        result = await session.execute(
            select(Position).where(
                Position.env_mode == settings.env_mode.value,
                # 负数量 = Short Position
                Position.quantity < 0,
            )
        )
        positions = list(result.scalars().all())

        if not positions:
            logger.debug("📋 No short positions — lifecycle scan skipped")
            return

        logger.info(f"📋 Found {len(positions)} short positions to scan")

        # ── 构造 PositionSnapshot 列表 ──
        snapshots = await _build_position_snapshots(positions)

        if not snapshots:
            logger.debug("📋 No scannable snapshots — lifecycle scan skipped")
            return

        # ── 触发生命周期引擎 ──
        from app.services.strategy_lifecycle import scan_portfolio_lifecycle
        signals = scan_portfolio_lifecycle(snapshots)

        if not signals:
            logger.info("✅ All positions healthy — no action needed")
            return

        logger.info(f"⚡ Lifecycle engine produced {len(signals)} signals")

        # ── 逐一执行信号 ──
        for signal in signals:
            try:
                await _execute_lifecycle_signal(session, signal, settings)
            except Exception as e:
                logger.error(
                    f"Failed to execute signal for {signal.target_ticker}: {e}"
                )


async def _build_position_snapshots(
    positions: list[Position],
) -> list[PositionSnapshot]:
    """
    将 ORM Position 转换为 PositionSnapshot DTO

    TODO: 从 broker 拉取当前市价 (current_cost / underlying_price)
    当前使用 mock 值以确保代码通路畅通
    """
    snapshots: list[PositionSnapshot] = []

    for pos in positions:
        try:
            # 判断持仓类型 (简化: 基于 ticker 格式和 quantity 方向)
            if pos.quantity < 0:
                # Short position — 需要区分 put 和 call
                # TODO: 从订单历史关联推导 position_type
                position_type = "short_put"  # 默认, 需要后续优化
            else:
                continue  # Long position 不在巡检范围

            snapshot = PositionSnapshot(
                ticker=pos.ticker,
                contract_symbol=None,  # TODO: 从 order history 关联
                position_type=position_type,
                quantity=pos.quantity,
                strike=None,           # TODO: 从 contract symbol 解析
                expiration=None,       # TODO: 从 contract symbol 解析
                initial_premium=abs(pos.avg_cost_basis),  # 卖出时收取的权利金
                current_cost=abs(pos.avg_cost_basis) * 0.4,  # TODO: 实时行情
                underlying_price=500.0,  # TODO: 从 broker 拉取
            )
            snapshots.append(snapshot)
        except Exception as e:
            logger.warning(f"Failed to build snapshot for {pos.ticker}: {e}")

    return snapshots


async def _execute_lifecycle_signal(session, signal, settings) -> None:
    """
    执行生命周期信号 — BUY_TO_CLOSE / ROLL_OUT

    BUY_TO_CLOSE: 直接提交 OMS 平仓单
    ROLL_OUT: 平旧 + 开新 (两步订单, 先平后开)
    """
    from app.adapters.paper import PaperBrokerAdapter
    from app.schemas.order import OrderAction, OrderCreate
    from app.services.order_manager import OrderManagerService

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    broker = PaperBrokerAdapter()
    oms = OrderManagerService(db=session, broker=broker)

    if signal.action_type == ActionType.BUY_TO_CLOSE:
        order_dto = OrderCreate(
            ticker=signal.target_ticker,
            action=OrderAction.BUY,
            action_type="Buy to Close",
            order_type="limit_price_chaser",
            strike=signal.execution_details.strike_price,
            expiration=signal.execution_details.expiration,
            quantity=1,
            limit_price=signal.execution_details.limit_price,
            idempotency_key=uuid.uuid4(),
        )
        order = await oms.submit_order(order_dto)
        logger.info(
            f"💰 Take-profit order: {order.id} {signal.target_ticker} "
            f"scene={signal.scene_label}"
        )

    elif signal.action_type == ActionType.ROLL_OUT:
        # Step 1: 平掉旧合约
        close_dto = OrderCreate(
            ticker=signal.target_ticker,
            action=OrderAction.BUY,
            action_type="Buy to Close",
            order_type="limit_price_chaser",
            strike=signal.execution_details.strike_price,
            expiration=signal.execution_details.expiration,
            quantity=1,
            limit_price=signal.execution_details.limit_price,
            idempotency_key=uuid.uuid4(),
        )
        close_order = await oms.submit_order(close_dto)
        logger.info(
            f"🔄 Roll-out close leg: {close_order.id} {signal.target_ticker}"
        )

        # Step 2: 开新合约 (下月, 同或更低 strike)
        # TODO: 调用 strategy_entry 的 _find_optimal_strike 选择新合约
        # 目前仅记录日志, 等期权链查询功能就绪后补全
        logger.info(
            f"🔄 Roll-out open leg: pending option chain query for "
            f"{signal.target_ticker}"
        )


# ══════════════════════════════════════════════════════════════
# 子任务 B: 券商对账 (Reconciliation Daemon)
# ══════════════════════════════════════════════════════════════


async def _run_reconciliation(settings) -> None:
    """
    独立对账 — 拉取券商真实持仓 vs 本地 DB

    对账是交易系统最重要的安全网:
    - 网络抖动导致订单状态未同步
    - 券商回调丢失
    - 手动在券商端操作但未同步到系统

    发现 MISMATCH 时:
    1. 记录 CRITICAL 级别日志 (触发告警)
    2. 不自动修复 — 人工确认后再处理 (安全第一)
    """
    async with get_async_session() as session:
        # ── 拉取券商真实持仓 ──
        from app.adapters.paper import PaperBrokerAdapter
        broker = PaperBrokerAdapter()

        try:
            broker_positions = await broker.get_positions()
        except Exception as e:
            logger.error(f"Failed to fetch broker positions: {e}")
            return

        # ── 拉取本地 DB 持仓 ──
        result = await session.execute(
            select(Position).where(
                Position.env_mode == settings.env_mode.value,
            )
        )
        local_positions = {p.ticker: p for p in result.scalars().all()}

        # ── 比对逻辑 ──
        mismatch_count = 0

        # Check 1: 券商有但本地没有 (幽灵持仓)
        for bp in broker_positions:
            local = local_positions.get(bp.ticker)
            if local is None:
                logger.critical(
                    f"🚨 RECON MISMATCH: {bp.ticker} exists at broker "
                    f"(qty={bp.quantity}) but NOT in local DB! "
                    f"Possible missed fill or manual broker trade."
                )
                mismatch_count += 1
                continue

            # Check 2: 数量不一致
            if local.quantity != bp.quantity:
                logger.critical(
                    f"🚨 RECON MISMATCH: {bp.ticker} quantity divergence — "
                    f"broker={bp.quantity} vs local={local.quantity}. "
                    f"Delta={bp.quantity - local.quantity}"
                )
                mismatch_count += 1

            # Check 3: 成本差异 > 5% (允许微小的计算误差)
            if local.avg_cost_basis > 0 and bp.avg_cost > 0:
                cost_diff_pct = abs(
                    local.avg_cost_basis - bp.avg_cost
                ) / local.avg_cost_basis * 100
                if cost_diff_pct > 5.0:
                    logger.warning(
                        f"⚠️ RECON DRIFT: {bp.ticker} cost basis divergence — "
                        f"broker=${bp.avg_cost:.2f} vs local=${local.avg_cost_basis:.2f} "
                        f"(diff={cost_diff_pct:.1f}%)"
                    )

            # 标记已比对
            local_positions.pop(bp.ticker, None)

        # Check 4: 本地有但券商没有 (本地幻影)
        for ticker, local in local_positions.items():
            if local.quantity != 0:  # 忽略已清仓的记录
                logger.critical(
                    f"🚨 RECON MISMATCH: {ticker} exists in local DB "
                    f"(qty={local.quantity}) but NOT at broker! "
                    f"Possible missed cancellation or broker liquidation."
                )
                mismatch_count += 1

        # ── 汇总报告 ──
        if mismatch_count > 0:
            logger.critical(
                f"🚨 RECONCILIATION ALERT: {mismatch_count} mismatches detected! "
                f"Manual review required."
            )
            # TODO: 推送告警 (Slack/Email/PagerDuty)
        else:
            logger.info(
                f"✅ Reconciliation passed: "
                f"{len(broker_positions)} broker positions verified"
            )
