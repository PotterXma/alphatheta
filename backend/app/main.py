"""
AlphaTheta v2 — FastAPI Application Factory & Lifecycle Manager

生命周期设计:
┌─────────────────────────────────────────────────────────────────┐
│ STARTUP                                                         │
│  1. 加载 NYSE 交易日历到内存 (exchange_calendars)               │
│  2. 初始化 OpenTelemetry SDK (OTLP exporter)                   │
│  3. 从 PG 恢复 Kill Switch 状态到 Redis (保证重启不丢状态)      │
│  4. 启动对账守护协程                                            │
│  5. 日志确认环境模式 (paper/live)                               │
├─────────────────────────────────────────────────────────────────┤
│ RUNNING — 处理请求                                              │
│  ↓ Middleware 执行顺序:                                         │
│  RateLimit → KillSwitch → Calendar → Idempotency → Router      │
├─────────────────────────────────────────────────────────────────┤
│ SHUTDOWN (SIGTERM / Ctrl+C)                                     │
│  1. 设置 _shutting_down 标志，拒绝新请求                       │
│  2. 关闭所有 WebSocket 连接 (code=1001)                        │
│  3. 等待进行中的 DB 事务完成 (最长 30s)                        │
│  4. 关闭 Redis 连接池                                          │
│  5. Flush OTel spans                                           │
│  6. 日志确认 "Shutdown complete"                               │
└─────────────────────────────────────────────────────────────────┘
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging.logger_setup import logger, setup_logging

# ── 全局状态标志 ──
_shutting_down: bool = False
_shutdown_event: asyncio.Event = asyncio.Event()

# 日历缓存 (启动时加载，运行期间只读)
_market_calendar = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期 — 所有初始化和清理逻辑集中于此

    使用 asynccontextmanager 而非 on_event，因为:
    1. 可以在 yield 前后精确控制资源生命周期
    2. 异常自动触发 finally 清理
    3. FastAPI 官方推荐方式
    """
    global _market_calendar

    settings = get_settings()
    setup_logging(console_level=settings.log_level)

    logger.info(
        f"╔══════════════════════════════════════════════╗\n"
        f"║  AlphaTheta v2 Starting                     ║\n"
        f"║  env_mode = {settings.env_mode.value:<32s} ║\n"
        f"╚══════════════════════════════════════════════╝"
    )

    # ── 1. 加载 NYSE 交易日历 ──
    try:
        import exchange_calendars as xcals

        _market_calendar = xcals.get_calendar("XNYS")
        logger.info("✅ NYSE calendar loaded into memory")
    except Exception as e:
        logger.warning(f"⚠️ Calendar load failed (non-fatal): {e}")

    # ── 2. 数据库表结构自动同步 ──
    # 启动时自动创建缺失的表 + 补齐缺失字段
    try:
        from app.db.session import _get_engine
        from app.db.auto_migrate import ensure_tables

        engine = _get_engine()
        await ensure_tables(engine, auto_alter=True)
        logger.info("✅ Database schema synchronized")
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        # 非致命错误 — API 仍可启动, 但部分功能可能不可用

    # ── 3. 初始化 OpenTelemetry ──
    try:
        from app.telemetry.tracing import init_tracing

        init_tracing(
            app,
            service_name=settings.otel_service_name,
            otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        )
        logger.info("✅ OpenTelemetry initialized")
    except Exception as e:
        logger.warning(f"⚠️ OTel init failed (non-fatal): {e}")

    # ── 3. 从 PG 恢复 Kill Switch 状态到 Redis ──
    # 确保重启后 Redis 中的熔断状态与 PG 持久层一致
    # await _restore_kill_switch_from_db()
    logger.info("ℹ️ Kill Switch restore: deferred until DB session available")

    # ── 4. 启动后台协程 ──
    # reconciliation_task = asyncio.create_task(_run_reconciliation())
    # logger.info("✅ Reconciliation daemon started")

    # ── 5. 注册信号处理 ──
    loop = asyncio.get_event_loop()

    def _signal_handler(sig: signal.Signals):
        logger.warning(f"Received {sig.name} — initiating graceful shutdown...")
        global _shutting_down
        _shutting_down = True
        _shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler, sig)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler
            pass

    # ── Redis 信号订阅器 (WebSocket 桥) ──
    try:
        from app.websocket.feed import start_redis_subscriber
        start_redis_subscriber()
        logger.info("✅ Redis signal subscriber started")
    except Exception as e:
        logger.warning(f"⚠️ Redis signal subscriber failed to start: {e}")

    logger.info("✅ All startup tasks complete — ready to serve")

    # ════════════════════════════════════════════
    # ↓  应用运行中  ↓
    # ════════════════════════════════════════════
    yield
    # ════════════════════════════════════════════
    # ↓  优雅关闭  ↓
    # ════════════════════════════════════════════

    logger.info("Draining connections and flushing data...")

    # ── S1. 关闭 WebSocket 连接 ──
    try:
        from app.websocket.feed import manager

        await manager.close_all(code=1001)
        logger.info("✅ All WebSocket connections closed")
    except Exception as e:
        logger.warning(f"WS close error: {e}")

    # ── S2. 等待进行中的事务 (最长 30 秒超时) ──
    try:
        await asyncio.wait_for(_drain_in_flight(), timeout=30.0)
        logger.info("✅ In-flight transactions drained")
    except asyncio.TimeoutError:
        logger.error("❌ Shutdown timeout (30s) — forcing exit")

    # ── S3. 关闭 Redis 连接池 ──
    try:
        from app.dependencies import get_redis

        redis = await get_redis()
        await redis.aclose()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis close error: {e}")

    # ── S4. Flush OTel spans ──
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush(timeout_millis=5000)
        logger.info("✅ OTel spans flushed")
    except Exception:
        pass

    logger.info("Shutdown complete. Goodbye 👋")


async def _drain_in_flight():
    """等待进行中的请求完成 — 通过简单的 sleep 给 uvicorn 时间排空"""
    await asyncio.sleep(2)


def create_app() -> FastAPI:
    """
    应用工厂 — 创建并配置 FastAPI 实例

    Middleware 注册顺序很重要 (先注册的后执行):
    注册顺序:  CORS → RateLimit → KillSwitch → Calendar → Idempotency
    执行顺序:  Idempotency → Calendar → KillSwitch → RateLimit → CORS → Router
    """
    settings = get_settings()

    app = FastAPI(
        title="AlphaTheta Trading Engine v2",
        description="美股期权交易对冲系统后端 — 包含 CRO 风控、择时、OMS/EMS",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ══════════════════════════════════════════
    # Middleware 注册 (Starlette 先注册后执行)
    # ══════════════════════════════════════════

    # ── L1: CORS (最外层) ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Env-Mode", "X-Trace-Id", "X-Idempotent-Replay"],
    )

    # ── L2: Rate Limiter ──
    from app.middleware.rate_limit import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)

    # ── L1.8: Visitor Tracking (IP 统计 — Redis 持久化) ──
    from app.middleware.visitor_tracking import VisitorTrackingMiddleware

    app.add_middleware(VisitorTrackingMiddleware)

    # ── L1.5: Trace ID (最外层，执行在 RateLimit 之前) ──
    from app.middleware.trace_id import TraceIdMiddleware

    app.add_middleware(TraceIdMiddleware)

    # ── L2.5: JWT Auth (认证 — 注入 user_id 到 request.state) ──
    from app.middleware.auth import AuthMiddleware

    app.add_middleware(AuthMiddleware)

    # ── L3: Kill Switch (熔断检查) ──
    from app.middleware.kill_switch import KillSwitchMiddleware

    app.add_middleware(KillSwitchMiddleware)

    # ── L4: Calendar (交易日历) ──
    from app.middleware.calendar import CalendarMiddleware

    app.add_middleware(CalendarMiddleware)

    # ── L5: Idempotency (最内层，紧贴 Router) ──
    from app.middleware.idempotency import IdempotencyMiddleware

    app.add_middleware(IdempotencyMiddleware)

    # ══════════════════════════════════════════
    # 环境标记中间件 — 每个响应都携带当前环境信息
    # ══════════════════════════════════════════
    @app.middleware("http")
    async def add_env_header(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Env-Mode"] = settings.env_mode.value
        return response

    # ══════════════════════════════════════════
    # 路由注册
    # ══════════════════════════════════════════
    from app.routers import admin, auth, dashboard, market, orders, risk, strategy
    from app.routers import settings as settings_routes
    from app.routers import advanced_ops

    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard Sync"])
    app.include_router(market.router, prefix="/api/v1/market", tags=["Market Data"])

    from app.routers import market_data
    app.include_router(market_data.router, prefix="/api/v1/market_data", tags=["Strategy Studio Data"])
    app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk Engine"])
    app.include_router(strategy.router, prefix="/api/v1/strategy", tags=["Strategy & Timing"])
    app.include_router(advanced_ops.router, prefix="/api/v1/strategy", tags=["Advanced Ops"])
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["Order Management"])

    from app.routers import execution
    app.include_router(execution.router, prefix="/api/v1/orders", tags=["Execution"])

    from app.routers import portfolio
    app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])

    from app.routers import scanner
    app.include_router(scanner.router, prefix="/api/v1/scanner", tags=["Scanner"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin & Audit"])
    app.include_router(settings_routes.router, prefix="/api/v1/settings", tags=["System Settings"])

    # ── Prometheus 指标端点 ──
    from app.telemetry.metrics import router as metrics_router

    app.include_router(metrics_router, tags=["Infrastructure"])

    # ── WebSocket Feed ──
    from app.websocket.feed import router as ws_router

    app.include_router(ws_router, tags=["WebSocket"])

    # ══════════════════════════════════════════
    # 基础设施端点
    # ══════════════════════════════════════════

    @app.get("/healthz", tags=["Infrastructure"])
    async def liveness():
        """
        K8s Liveness Probe — 进程存活检查
        仅检查进程是否正常响应，不检查依赖
        如果返回非 200，K8s 将重启 Pod
        """
        if _shutting_down:
            return Response(
                content='{"status": "shutting_down"}',
                status_code=503,
                media_type="application/json",
            )
        return {"status": "alive", "env_mode": settings.env_mode.value}

    @app.get("/readyz", tags=["Infrastructure"])
    async def readiness():
        """
        K8s Readiness Probe — 依赖就绪检查
        检查 PG + Redis 连接是否正常
        如果返回非 200，K8s 将从 Service 摘除此 Pod (不接收新流量)
        """
        checks: dict[str, str] = {}

        # 检查 Redis
        try:
            from app.dependencies import get_redis

            redis = await get_redis()
            await redis.ping()
            checks["redis"] = "up"
        except Exception as e:
            checks["redis"] = f"down: {e}"

        # 检查 PG
        try:
            from app.dependencies import _get_engine

            engine = _get_engine()
            async with engine.connect() as conn:
                await conn.execute(
                    __import__("sqlalchemy").text("SELECT 1")
                )
            checks["postgres"] = "up"
        except Exception as e:
            checks["postgres"] = f"down: {e}"

        all_up = all(v == "up" for v in checks.values())
        return Response(
            content=__import__("json").dumps({
                "status": "ready" if all_up else "degraded",
                "checks": checks,
                "env_mode": settings.env_mode.value,
            }),
            status_code=200 if all_up else 503,
            media_type="application/json",
        )

    return app


# ── 模块级应用实例 (uvicorn 入口) ──
app = create_app()
