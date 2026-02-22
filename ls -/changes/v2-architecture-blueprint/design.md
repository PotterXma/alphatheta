## Context

AlphaTheta v2 is a single-user options trading prototype with mock data, `Float`-precision prices, and no real execution pipeline. The current architecture (FastAPI + PostgreSQL + Redis + Nginx) is sound but lacks multi-tenancy, autonomous scanning, and broker integration. The `001_core_schema.sql` DDL and `db/auto_migrate.py` auto-sync layer are already in place. This design covers the 6 new capabilities needed to reach production SaaS status.

### Current State
- **DB**: Auto-migration engine creates tables on boot. Existing models use `Float` and are single-tenant.
- **API**: FastAPI with 5-layer middleware (CORS → RateLimit → KillSwitch → Calendar → Idempotency). No auth.
- **Frontend**: Dark glassmorphism SPA with Strategy Studio, portfolio tracker, settings, health terminal.
- **Infra**: docker-compose with `api`, `web`, `db`, `redis` containers.

## Goals / Non-Goals

**Goals:**
- Multi-tenant data isolation with JWT auth and row-level `user_id` scoping
- Autonomous scanner daemon running 7×24 with RSI → IVR two-stage LEAPS filtering
- Real-time signal delivery via Redis pub/sub → WebSocket → frontend toast
- Reg T margin calculation for pre-trade buying power validation
- Corporate action lifecycle management (splits, dividends, early assignment)
- ORM models aligned with `001_core_schema.sql` DDL (DECIMAL prices, enums, FKs)

**Non-Goals:**
- Portfolio margin (Reg T only for v2)
- Multi-broker support (TastyTrade only for v2)
- Mobile app or PWA
- Backtesting engine (future v3)
- Options auto-exercise logic (broker handles this)

## Decisions

### D1: Auth — JWT + Fernet credential vault
- **Choice**: Stateless JWT (access 15min + refresh 7d) stored in `httpOnly` cookies. Broker secrets encrypted with `cryptography.fernet`.
- **Rationale**: No session table needed. Fernet is symmetric + authenticated (HMAC). Simpler than asymmetric for single-service architecture.
- **Alternative rejected**: OAuth2 social login — adds complexity, our users are technical traders who prefer direct credentials.

### D2: Scanner — Standalone asyncio process, NOT Celery
- **Choice**: Single-file `scanner/main.py` running as its own container, using `asyncio.sleep` for scheduling.
- **Rationale**: Celery adds Redis broker complexity and Beat scheduler overhead. Our loop is simple: wake → scan → sleep. No task queue needed.
- **Alternative rejected**: Celery Beat — overkill for a single recurring job with no fan-out.

### D3: Signal delivery — Redis pub/sub + WebSocket
- **Choice**: Scanner publishes to `channel:signals:{user_id}`. API subscribes per-user via WebSocket connection. Frontend renders Toast.
- **Rationale**: Redis pub/sub is fire-and-forget (no persistence needed — signals are ephemeral). WebSocket already exists in the codebase.
- **Key constraint**: Signal deduplication via Redis SET with 24h TTL keyed by OCC symbol.

### D4: Margin — Reg T simplified formula
- **Choice**: Implement standard Reg T formulas (naked put = 20% underlying + premium - OTM amount; covered call = stock cost - call premium).
- **Rationale**: Reg T is the industry standard for retail. Portfolio margin is complex and broker-specific (future).
- **Key constraint**: Must run BEFORE order submission, using `SELECT ... FOR UPDATE` on `users.cash_balance`.

### D5: Corporate actions — Daily poll, NOT webhook
- **Choice**: Daily 6:00 AM EST cron job checking a corporate actions API (e.g., Polygon.io or free Yahoo endpoint).
- **Rationale**: Webhooks from data providers are unreliable and expensive. Splits/dividends are announced days in advance — daily check is sufficient.

### D6: ORM upgrade — Incremental, auto_migrate handles drift
- **Choice**: Rewrite models one-by-one. `auto_migrate.py` handles the ADD COLUMN / ALTER TYPE drift automatically on restart.
- **Rationale**: No need for Alembic migration scripts in dev — the auto-sync engine already reconciles model vs DB.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scanner daemon crashes silently | Missed signals for hours | Heartbeat ping to Redis every cycle. Health console checks last heartbeat. Auto-restart via docker `restart: unless-stopped`. |
| JWT token stolen | Unauthorized trading | `httpOnly` + `Secure` + `SameSite=Strict` cookies. Short access token TTL (15min). Refresh rotation. |
| Fernet key rotation | Existing encrypted secrets become unreadable | Store key version in `user_broker_credentials.key_version`. Support decrypting with old key during rotation window. |
| Float → DECIMAL migration | Existing data precision loss | One-time migration script with explicit CAST. No existing production data yet (paper only). |
| Reg T formula edge cases | Incorrect margin calculation → over/under-collateralization | Conservative: always round UP margin requirement. Log discrepancies for manual review. |
| Redis pub/sub message loss | User misses signal | Acceptable for v2 (signals are also logged to DB). Future: Redis Streams for at-least-once delivery. |
