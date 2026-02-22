## Implementation Tasks

### Phase 1: ORM Model Upgrade (Foundation)
_Everything else depends on `user_id` FK existing in models._

- [x] **T1.1** Create `app/models/user.py` — `User` model with UUID PK, `cash_balance` Numeric(14,4), CHECK constraints
- [x] **T1.2** Create `app/models/user_broker_credentials.py` — Fernet-encrypted fields, `UNIQUE(user_id)`
- [x] **T1.3** Rewrite `app/models/order.py` — Add `user_id` FK, rename table to `orders_master`, migrate `Float` → `Numeric(12,4)`, add proper `OrderStatus` enum
- [x] **T1.4** Create `app/models/order_leg.py` — `OrderLeg` model with OCC symbol, `entry_greeks` JSONB, `trade_action`/`option_right` enums
- [x] **T1.5** Rewrite `app/models/position.py` — Add `user_id` FK, `occ_symbol`, `net_quantity` (signed), `realized_pnl`, `UNIQUE(user_id, occ_symbol)`
- [x] **T1.6** Rewrite `app/models/watchlist.py` — Add `user_id` FK (remove ticker-as-PK), `risk_limit_pct` Numeric, `UNIQUE(user_id, ticker)`
- [x] **T1.7** Update `app/models/__init__.py` — Import all new/rewritten models
- [x] **T1.8** Verify: restart API → `auto_migrate` creates/alters all tables without errors

---

### Phase 2: Multi-Tenant Auth
- [x] **T2.1** Add dependencies: `PyJWT`, `passlib[bcrypt]`, `cryptography` to `requirements.txt`
- [x] **T2.2** Create `app/services/auth.py` — `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`
- [x] **T2.3** Create `app/services/crypto_vault.py` — `encrypt_secret(plaintext)`, `decrypt_secret(ciphertext)` using Fernet from `FERNET_KEY` env var
- [x] **T2.4** Create `app/routers/auth.py` — `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
- [x] **T2.5** Create `app/middleware/auth.py` — `AuthMiddleware` that extracts JWT from `Authorization` header or cookie, resolves `user_id`, injects into `request.state.user_id`
- [x] **T2.6** Create `app/dependencies.py:get_current_user()` — FastAPI dependency that reads `request.state.user_id` and returns `User` ORM object
- [x] **T2.7** Update all existing routers — Add `current_user: User = Depends(get_current_user)` and scope all queries by `user_id`
- [x] **T2.8** Verify: register → login → access protected endpoint → token refresh → cross-tenant 404

---

### Phase 3: Scanner Daemon
- [x] **T3.1** Create `scanner/` directory with `__init__.py`, `main.py`, `filters.py`, `config.py`
- [x] **T3.2** Implement `scanner/main.py` — asyncio event loop with `exchange_calendars` scheduling (15min cycle during market hours)
- [x] **T3.3** Implement `scanner/filters.py` — `stage1_rsi_filter(ticker)` and `stage2_leaps_deep_dive(ticker, option_chain)`
- [x] **T3.4** Implement Redis signal publishing — `signals:broadcast` channel, `signals:dedup` SET with 24h TTL
- [x] **T3.5** Add `scanner` service to `docker-compose.yml` — `restart: unless-stopped`, shares `redis` and `db` networks
- [x] **T3.6** Implement heartbeat — write `scanner:heartbeat` key every cycle, health console checks it
- [x] **T3.7** Verify: start scanner → observe RSI filter logs → verify signal publish to Redis

---

### Phase 4: Real-Time Signal Pipeline
- [x] **T4.1** Update `app/websocket/feed.py` — Add Redis pub/sub subscriber for `signals:broadcast`, filter by user's watchlist
- [x] **T4.2** Add WebSocket JWT auth — Validate token from `?token=` query param on WS connect
- [x] **T4.3** Frontend: Add WebSocket signal listener in `js/store/index.js` → dispatch to Toast component
- [x] **T4.4** Implement webhook delivery — `app/services/notification.py:send_webhooks(user_id, signal)` — fire-and-forget POST to configured endpoints
- [x] **T4.5** Verify: mock signal → Redis publish → WebSocket delivery → toast rendered

---

### Phase 5: Margin Engine
- [x] **T5.1** Create `app/services/margin.py` — `calculate_margin(strategy_type, legs, underlying_price)` with Reg T formulas
- [x] **T5.2** Implement `validate_buying_power(user_id, required_margin)` — `SELECT ... FOR UPDATE` on `users`, check `cash_balance - margin_used >= required_margin`
- [x] **T5.3** Integrate into order submission flow — call `validate_buying_power` before `orders_master` INSERT
- [x] **T5.4** Implement margin release on cancel — return pre-deducted margin to `cash_balance`
- [x] **T5.5** Verify: submit order with insufficient funds → REJECTED. Submit with sufficient → margin deducted. Cancel → refunded.

---

### Phase 6: Corporate Action Handler
- [x] **T6.1** Create `app/scheduler/corporate_actions.py` — daily 06:00 EST job to check splits/dividends
- [x] **T6.2** Implement `handle_split(ticker, ratio)` — adjust `user_positions` quantity/strike/OCC, log to `audit_log`
- [x] **T6.3** Implement early assignment radar — check short ITM calls within 3 days of ex-dividend, push CRITICAL alert
- [x] **T6.4** Add corporate action check to scanner daemon's daily pre-market routine
- [x] **T6.5** Verify: simulate 4:1 split → positions adjusted correctly. Simulate ex-div near ITM short call → alert fired.
