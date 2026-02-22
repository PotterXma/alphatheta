## 1. DB Session Factory (`db/session.py`)

- [x] 1.1 `get_async_session()` — async context manager with auto commit/rollback
- [x] 1.2 Lazy singleton engine + session factory
- [x] 1.3 `close_engine()` — shutdown 时释放连接池

## 2. Scheduler Core (`scheduler/core.py`)

- [x] 2.1 `AsyncIOScheduler` singleton with coalesce/max_instances=1
- [x] 2.2 `start_scheduler()` — 注册 2 个 IntervalTrigger 任务
- [x] 2.3 `stop_scheduler()` — wait=True 优雅停止
- [x] 2.4 Package init files (__init__.py × 2)

## 3. Task 1: Market Scanner (`scheduler/tasks/market_scanner.py`)

- [x] 3.1 `_is_market_open()` — NYSE exchange_calendars 精确到分钟
- [x] 3.2 休市跳过 (debug log)
- [x] 3.3 组装 StrategyMarketContext (VIX + RSI + 持仓查询)
- [x] 3.4 调用 evaluate_market_entry() 触发决策树
- [x] 3.5 非 HOLD → `_auto_submit_order()` 自动发单
- [x] 3.6 幂等 Key: scanner_{ticker}_{date}_{uuid}
- [x] 3.7 全局 try-except 防崩溃

## 4. Task 2: Portfolio Auditor (`scheduler/tasks/portfolio_auditor.py`)

- [x] 4.1 子任务隔离: lifecycle + recon 独立 try-except
- [x] 4.2 Lifecycle Scan: DB 读取 short positions → PositionSnapshot → signals
- [x] 4.3 Auto-exec: BUY_TO_CLOSE (止盈) / ROLL_OUT (展期两步)
- [x] 4.4 Reconciliation: broker vs local 四维比对
- [x] 4.5 Ghost position 检测 (券商有/本地无)
- [x] 4.6 Phantom position 检测 (本地有/券商无)
- [x] 4.7 Quantity divergence → CRITICAL log
- [x] 4.8 Cost drift > 5% → WARNING log
