## Why

AlphaTheta v2 currently operates as a single-user prototype with mock data, Float-precision prices, and no real execution pipeline. To graduate to a production SaaS capable of managing real capital across multiple tenants, the system needs: multi-tenant data isolation, financial-grade data types, a 7×24 autonomous scanning daemon, and broker-integrated execution with pessimistic fund locking. Without this foundation, no feature built on top is trustworthy for live trading.

## What Changes

- **[NEW]** JWT-based multi-tenant authentication with encrypted broker credential storage
- **[NEW]** Standalone scanner daemon process (asyncio) with RSI → IVR two-stage filtering pipeline
- **[NEW]** Redis pub/sub real-time signal delivery (daemon → API → WebSocket → frontend toast)
- **[NEW]** Reg T margin calculation engine for mixed stock + options positions
- **[NEW]** Corporate action lifecycle handler (stock splits, dividends, early assignment radar)
- **[NEW]** ORM model rewrite: all models gain `user_id` FK, prices migrate from `Float` to `DECIMAL(12,4)`
- **[BREAKING]** All API endpoints require `Authorization: Bearer <JWT>` header
- **[BREAKING]** Database schema changes: existing single-tenant tables migrated to multi-tenant with `user_id` column

## Capabilities

### New Capabilities

- `multi-tenant-auth`: JWT authentication, user registration/login, row-level tenant isolation, encrypted credential vault (AES-256-GCM for broker API secrets)
- `scanner-daemon`: Standalone asyncio process. 15-min wake cycle during EST market hours. Deduplicated global watchlist scan. RSI < 35 pre-filter → LEAPS option chain deep dive (IVR, DTE, liquidity). Redis signal publish.
- `realtime-signal-pipe`: Redis pub/sub channel schema. WebSocket broadcast from API to connected frontends. Toast notification rendering. Signal deduplication (24h TTL per OCC symbol).
- `margin-engine`: Reg T margin calculation for naked puts, covered calls, and complex spreads (Iron Condor, PMCC). Mixed asset collateral netting. Pre-trade buying power validation with `SELECT ... FOR UPDATE`.
- `corporate-action-handler`: Daily corporate action poll (splits, dividends). Automatic position adjustment (quantity × ratio, strike ÷ ratio, OCC symbol regeneration). Early assignment radar: alert when short call is ITM within 3 days of ex-dividend.
- `orm-model-upgrade`: Rewrite all SQLAlchemy models to match `001_core_schema.sql` DDL. Multi-tenant FKs, `DECIMAL(12,4)` prices, `TIMESTAMPTZ` everywhere, proper enums, and relationship definitions.

### Modified Capabilities

_None — no existing specs to modify._

## Impact

- **Database**: All tables gain `user_id` FK. Price columns migrate `Float → Numeric(12,4)`. New tables: `users`, `user_broker_credentials`. Existing data requires migration script.
- **API**: Every router needs auth middleware injection. New `/auth/login`, `/auth/register` endpoints. All existing endpoints become tenant-scoped.
- **Frontend**: Login/register flow. JWT token management (localStorage + refresh). All API calls add `Authorization` header.
- **Infrastructure**: New `scanner-daemon` container in docker-compose. Redis upgraded from cache-only to pub/sub hub. PM2/Systemd process management for daemon.
- **Dependencies**: `PyJWT`, `passlib[bcrypt]`, `cryptography` (Fernet), `exchange_calendars`, `ta-lib` or `pandas_ta` (RSI).
