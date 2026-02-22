"""
企业行动处理器 — 日度盘前巡检

每日 06:00 EST (盘前) 执行:
1. 股票拆分处理 (split)
   - 调整 user_positions 数量和行权价
   - 调整 OCC 合约代码
   - 写入 audit_log

2. 早期行权雷达 (early assignment)
   - 检测 ex-dividend 日前 3 天内的空头 ITM Call
   - 推送 CRITICAL 告警

3. 股息监控 (dividend)
   - 记录即将除权的持仓

⚠️ v2 初版使用定时轮询, 而非 webhook
   因为企业行动 webhook 可靠性差, 且每日一次足够
"""

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("alphatheta.corporate_actions")


async def handle_split(
    session: AsyncSession,
    ticker: str,
    ratio_from: int,
    ratio_to: int,
) -> int:
    """
    处理股票拆分

    Args:
        ticker: 标的代码 (如 NVDA)
        ratio_from: 拆分前 (如 1)
        ratio_to: 拆分后 (如 4, 表示 1:4 拆分)

    Returns:
        受影响的持仓数量
    """
    from app.models.position import Position
    from app.models.audit_log import AuditLog

    ratio = Decimal(str(ratio_to)) / Decimal(str(ratio_from))

    # 查找所有该标的的活跃持仓
    result = await session.execute(
        select(Position)
        .where(Position.underlying == ticker)
        .where(Position.net_quantity != 0)
    )
    positions = result.scalars().all()

    if not positions:
        logger.info(f"ℹ️ {ticker} 无活跃持仓, 跳过拆分处理")
        return 0

    adjusted_count = 0
    for pos in positions:
        old_qty = pos.net_quantity
        old_strike = pos.strike_price
        old_cost = pos.average_cost

        # 调整数量 (向下取整)
        pos.net_quantity = int(old_qty * int(ratio))

        # 调整行权价 (反向)
        if pos.strike_price:
            pos.strike_price = float(Decimal(str(old_strike)) / ratio)

        # 调整平均成本 (反向)
        pos.average_cost = float(Decimal(str(old_cost)) / ratio)

        # 审计日志
        log = AuditLog(
            event_type="corporate_action",
            entity_type="position",
            entity_id=str(pos.position_id),
            details={
                "action": "stock_split",
                "ticker": ticker,
                "ratio": f"{ratio_from}:{ratio_to}",
                "old_qty": old_qty,
                "new_qty": pos.net_quantity,
                "old_strike": old_strike,
                "new_strike": pos.strike_price,
            },
        )
        session.add(log)
        adjusted_count += 1

    logger.info(
        f"✅ {ticker} {ratio_from}:{ratio_to} 拆分处理完成: "
        f"{adjusted_count} 个持仓已调整"
    )
    return adjusted_count


async def check_early_assignment_risk(
    session: AsyncSession,
    dividends: list[dict],
) -> list[dict]:
    """
    早期行权雷达 — 检测 ex-dividend 前 ITM 空头 Call

    美股期权在 ex-dividend 日前可能被提前行权
    条件: 空头 Call (net_quantity < 0) + ITM + ex-div 3 天内

    Args:
        dividends: [{"ticker": "AAPL", "ex_date": "2026-02-25", "amount": 0.25}, ...]

    Returns:
        [{"position_id": ..., "ticker": ..., "risk_level": "CRITICAL"}, ...]
    """
    from app.models.position import Position
    from app.models.order_leg import OptionRight

    alerts = []
    today = date.today()

    for div in dividends:
        ticker = div["ticker"]
        ex_date = div["ex_date"]
        if isinstance(ex_date, str):
            from datetime import datetime
            ex_date = datetime.strptime(ex_date, "%Y-%m-%d").date()

        # ex-div 3 天内才需要检查
        if not (today <= ex_date <= today + timedelta(days=3)):
            continue

        # 查找空头 Call 持仓
        result = await session.execute(
            select(Position)
            .where(Position.underlying == ticker)
            .where(Position.right_type == OptionRight.CALL)
            .where(Position.net_quantity < 0)  # 空头
        )
        short_calls = result.scalars().all()

        for pos in short_calls:
            # 简化 ITM 判断: 需要当前价格, 这里用行权价 < 当前价
            # 实际应查实时价, 这里标记所有空头 Call
            alert = {
                "position_id": str(pos.position_id),
                "user_id": str(pos.user_id),
                "ticker": ticker,
                "strike": pos.strike_price,
                "expiration": str(pos.expiration_date),
                "quantity": pos.net_quantity,
                "ex_date": str(ex_date),
                "dividend_amount": div["amount"],
                "risk_level": "CRITICAL",
                "message": (
                    f"⚠️ Early assignment risk: {ticker} short Call "
                    f"${pos.strike_price} exp {pos.expiration_date} "
                    f"— ex-div {ex_date} (${div['amount']})"
                ),
            }
            alerts.append(alert)
            logger.warning(alert["message"])

    return alerts


async def daily_corporate_action_check(session: AsyncSession) -> dict:
    """
    日度企业行动巡检主入口

    Returns:
        {"splits_processed": N, "assignment_alerts": N, "dividends_monitored": N}
    """
    # TODO: 接入实际数据源 (Polygon.io / Yahoo Finance / Tradier)
    # v2 初版使用空列表占位, 待数据源接入后填充
    splits: list[dict] = []  # [{"ticker": "NVDA", "ratio_from": 1, "ratio_to": 10}]
    dividends: list[dict] = []  # [{"ticker": "AAPL", "ex_date": "2026-03-01", "amount": 0.25}]

    results = {
        "splits_processed": 0,
        "assignment_alerts": 0,
        "dividends_monitored": len(dividends),
    }

    # 拆分处理
    for split in splits:
        count = await handle_split(
            session, split["ticker"], split["ratio_from"], split["ratio_to"]
        )
        results["splits_processed"] += count

    # 早期行权雷达
    alerts = await check_early_assignment_risk(session, dividends)
    results["assignment_alerts"] = len(alerts)

    # TODO: 通过 NotificationManager 推送 CRITICAL 告警
    # for alert in alerts:
    #     await notifier.send_critical_alert(alert)

    logger.info(
        f"📋 Daily corporate action check: "
        f"splits={results['splits_processed']} "
        f"alerts={results['assignment_alerts']} "
        f"dividends={results['dividends_monitored']}"
    )

    return results
