## 1. Project Scaffold

- [x] 1.1 Create `backend/` with `pyproject.toml` (Python 3.12, FastAPI, SQLAlchemy, Redis, uvicorn, httpx, cryptography, exchange-calendars, opentelemetry-*, prometheus-client)
- [x] 1.2 Create `backend/.env.example` (DB_URL, REDIS_URL, TIMESCALE_URL, BROKER_PROVIDER, BROKER_API_KEY, BROKER_SECRET, ENCRYPTION_KEY, ENV_MODE=paper|live, NTP_SERVER)
- [x] 1.3 Create `backend/app/main.py` — FastAPI app factory with lifespan (startup: load calendar, init OTel, restore kill switch; shutdown: graceful drain)
- [x] 1.4 Create `backend/app/config.py` — Pydantic Settings with Paper/Live env isolation, DB schema prefix switching
- [x] 1.5 Create `backend/app/dependencies.py` — DI providers (DB session, Redis, broker adapter factory based on ENV_MODE)
- [x] 1.6 Create `backend/Dockerfile` + `docker-compose.yml` (app + postgres + timescaledb + redis)
- [x] 1.7 Create `backend/k8s/` — deployment.yaml (2 replicas), service.yaml, configmap.yaml with liveness/readiness probes

## 2. Database Models & Migrations

- [x] 2.1 `models/base.py` — SQLAlchemy async base, engine factory with schema prefix support
- [x] 2.2 `models/order.py` — Order ORM with status enum (Draft/Pending/Filled/PartialFill/Rejected/Cancelled), idempotency_key column
- [x] 2.3 `models/position.py` — Position (ticker, quantity, avg_cost_basis, unrealized_pnl)
- [x] 2.4 `models/audit_log.py` — AuditLog (append-only, severity, source, message, metadata JSON)
- [x] 2.5 `models/kill_switch.py` — KillSwitchState (active, activated_at, reason, env_mode)
- [x] 2.6 `models/api_key.py` — ApiKey (provider, encrypted_key, encrypted_secret, mode)
- [x] 2.7 `models/tick.py` — TickData hypertable (time, ticker, bid, ask, last, volume) for TimescaleDB
- [x] 2.8 Alembic setup with multi-schema migration (paper_ / live_ prefix)

## 3. Pydantic Schemas (DTOs)

- [x] 3.1 `schemas/market.py` — MarketContext, Quote, Indicators, CalendarStatus
- [x] 3.2 `schemas/risk.py` — TradeProposal, RiskAssessment, ExecutionPlan, Playbooks
- [x] 3.3 `schemas/strategy.py` — TimingDecision, ProjectionRequest/Response, CorporateAction
- [x] 3.4 `schemas/order.py` — OrderCreate (with idempotency_key), OrderResponse, PositionResponse, RollRequest
- [x] 3.5 `schemas/admin.py` — ApiKeyCreate/Response (masked), KillSwitchToggle, LogEntry, HealthCheck, DailyReport

## 4. Middleware & Cross-Cutting

- [x] 4.1 `middleware/kill_switch.py` — Block POST/PUT/DELETE when kill switch active, env-aware
- [x] 4.2 `middleware/idempotency.py` — Extract Idempotency-Key header, check/store in Redis (TTL 24h), return cached response on duplicate
- [x] 4.3 `middleware/calendar.py` — Load exchange_calendars, reject mutating ops during market close, handle early close days
- [x] 4.4 `middleware/rate_limit.py` — 100 req/min per IP
- [x] 4.5 CORS middleware configuration for frontend origin

## 5. Telemetry & Observability

- [x] 5.1 `telemetry/tracing.py` — OpenTelemetry SDK init, FastAPI auto-instrument, httpx/SQLAlchemy/Redis instrument
- [x] 5.2 `telemetry/metrics.py` — Prometheus counters/histograms: api_latency, risk_rejections (by rule), orders_total, reconciliation_mismatches, ws_connections, kill_switch_activations
- [x] 5.3 `/healthz` (liveness), `/readyz` (readiness — checks PG + Redis), `/metrics` (Prometheus)
- [x] 5.4 Graceful shutdown handler: SIGTERM → stop accepting → drain WS → flush DB → exit within 30s

## 6. Broker Adapter Layer

- [x] 6.1 `adapters/broker_base.py` — Abstract ABC: submit_order, cancel_order, get_positions, get_quote, get_option_chain
- [x] 6.2 `adapters/tradier.py` — Tradier REST adapter with httpx async client
- [x] 6.3 `adapters/paper.py` — PaperBrokerAdapter: simulate fills locally with random latency (50-200ms)
- [x] 6.4 Retry logic (3× exponential backoff) + circuit breaker (30s cooldown after 5× 429s) in adapter base
- [x] 6.5 Request/response logging with TraceID propagation for all broker calls

## 7. Market & Calendar Service

- [x] 7.1 `services/market_calendar.py` — MarketCalendarService: get_quote, get_indicators, get_market_context, is_market_open
- [x] 7.2 On-demand OPRA subscription: subscribe/unsubscribe tickers, 5min idle timeout
- [x] 7.3 Redis caching: tick (30s TTL), indicators (60s TTL), VIX (60s TTL)
- [x] 7.4 RSI-14 calculation (Wilder smoothing), SMA200 distance, HV-30d
- [x] 7.5 TimescaleDB tick insertion (hypertable, 7-day chunks, 90-day retention)
- [x] 7.6 `routers/market.py` — GET /api/v1/market/{ticker}, GET /api/v1/market/calendar/status

## 8. Risk Engine Service

- [x] 8.1 `services/risk_engine.py` — 7 kill switch rules, sequential evaluation, first-trigger rejection
- [x] 8.2 Tax-aware yield: gross = (mid/strike)×(365/dte)×100, net = gross×(1-tax_drag)
- [x] 8.3 Execution plan: Limit_Price_Chaser, starting/floor limits, gross/net yield
- [x] 8.4 Scenario playbook generation (bull/bear/whipsaw with dynamic targets)
- [x] 8.5 Paper/Live environment validation: X-Env-Mode header check, adapter routing
- [x] 8.6 `routers/risk.py` — POST /api/v1/risk/evaluate

## 9. Strategy & Timing Service

- [x] 9.1 `services/strategy_timing.py` — 4-scene decision tree + VIX override + fallback
- [x] 9.2 Corporate actions parser: ex-dividend dates, stock splits → strike adjustment
- [x] 9.3 Pin Risk / DTE=0 auto-close: |delta| > 0.40 on expiry day → forced close order
- [x] 9.4 Sandbox projection calculator (covered_call + cash_secured_put formulas)
- [x] 9.5 `routers/strategy.py` — POST /api/v1/strategy/timing, POST /api/v1/strategy/project

## 10. Order Lifecycle Manager

- [x] 10.1 `services/order_manager.py` — create_order, submit_order (with Idempotency-Key), cancel_order
- [x] 10.2 State machine with strict transition validation + InvalidStateTransition exception
- [x] 10.3 Position tracking — atomic create/update on fills within same DB transaction
- [x] 10.4 Roll calculation engine (Up/Down/Out with estimated credit/debit)
- [x] 10.5 `services/reconciliation.py` — Independent daemon: compare broker positions vs local, flag discrepancies, auto-correct missed fills
- [x] 10.6 `routers/orders.py` — CRUD + submit + cancel + roll + positions

## 11. Admin, Audit & Reporting

- [x] 11.1 `services/admin.py` — API key CRUD (Fernet encryption), kill switch toggle (dual-write Redis+PG)
- [x] 11.2 `services/reporting.py` — Daily report aggregation: risk rejections, rolls, premium collected, loss avoided
- [x] 11.3 Audit log service — append-only create_log, paginated get_logs
- [x] 11.4 Kill switch startup recovery (PG → Redis sync)
- [x] 11.5 `routers/admin.py` — all admin + reports endpoints

## 12. WebSocket Feed

- [x] 12.1 `websocket/feed.py` — Channel subscriptions (market, orders, system_logs)
- [x] 12.2 asyncio.Queue broadcast mechanism
- [x] 12.3 Heartbeat ping/pong (30s), connection cleanup, graceful close on SIGTERM

## 13. Replay Engine

- [x] 13.1 `replay/runner.py` — CLI tool to load JSON tick fixtures and inject into market service
- [x] 13.2 `replay/fixtures/covid_crash_2020.json` — Historical VIX=82 extreme scenario
- [x] 13.3 Deterministic assertion framework: verify decision tree + risk engine outputs match expected
- [x] 13.4 CI integration: exit 0 on pass, exit 1 on fail
