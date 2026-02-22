"""
异步定时调度器核心 — APScheduler AsyncIOScheduler 封装

生命周期:
  FastAPI lifespan startup  → start_scheduler()  → 注册所有定时任务
  FastAPI lifespan shutdown → stop_scheduler()   → 优雅停止所有任务

设计原则:
1. 每个任务独立 try-except — 单个任务异常不会击溃调度器
2. 任务使用独立的 DB session — 不依赖 FastAPI Request 上下文
3. 交易时段校验 — 发单相关任务在休市期间自动跳过
4. 防并发: APScheduler 默认 max_instances=1, 防止慢任务堆积
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("alphatheta.scheduler")

# ── 模块级调度器单例 ──
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            # 线程池大小 — 后台任务不多, 2 个线程足够
            job_defaults={
                "coalesce": True,           # 如果错过多次执行, 只补执行一次
                "max_instances": 1,         # 同一任务同一时刻最多运行 1 个实例
                "misfire_grace_time": 60,   # 错过 60 秒内仍补执行
            },
        )
    return _scheduler


async def start_scheduler() -> None:
    """
    启动调度器并注册所有定时任务

    在 FastAPI lifespan 的 startup 阶段调用:
        async with lifespan(app):
            await start_scheduler()
            yield
            await stop_scheduler()
    """
    scheduler = get_scheduler()

    # ── 延迟导入任务函数 (避免循环依赖) ──
    from app.scheduler.tasks.market_scanner import run_market_scanner
    from app.scheduler.tasks.portfolio_auditor import run_portfolio_auditor

    # ════════════════════════════════════════
    # 任务 1: 策略择时心跳 — 每 5 分钟
    # ════════════════════════════════════════
    # 扫描大盘指标 (VIX/RSI), 触发开仓决策树
    # 休市期间自动跳过, 不会产生无效发单
    scheduler.add_job(
        run_market_scanner,
        trigger=IntervalTrigger(minutes=5),
        id="market_scanner",
        name="Strategy Heartbeat (5min)",
        replace_existing=True,
    )

    # ════════════════════════════════════════
    # 任务 2: 生命周期巡检 + 对账 — 每 30 分钟
    # ════════════════════════════════════════
    # 扫描持仓: 50% 止盈 / 21 DTE 展期
    # 拉取券商真实持仓做对账 (Reconciliation)
    scheduler.add_job(
        run_portfolio_auditor,
        trigger=IntervalTrigger(minutes=30),
        id="portfolio_auditor",
        name="Lifecycle & Recon (30min)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"🕐 Scheduler started: "
        f"{len(scheduler.get_jobs())} jobs registered"
    )
    for job in scheduler.get_jobs():
        logger.info(f"  → {job.name} (id={job.id}, trigger={job.trigger})")


async def stop_scheduler() -> None:
    """
    优雅停止调度器

    在 FastAPI lifespan 的 shutdown 阶段调用
    wait=True: 等待正在执行的任务完成后再关闭
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("🛑 Scheduler stopped gracefully")
        _scheduler = None
