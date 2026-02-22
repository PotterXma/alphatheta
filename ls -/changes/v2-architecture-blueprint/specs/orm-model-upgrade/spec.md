## ADDED Requirements

### Requirement: Multi-Tenant Model Upgrade
All ORM models gain `user_id` FK and use financial-grade data types.

#### Scenario: Order model upgrade
- **WHEN** the `Order` model is loaded
- **THEN** it MUST have: `user_id` UUID FK to `users`, `strike` as `Numeric(12,4)` (not Float), `status` as proper Enum with state machine, `filled_price` as `Numeric(12,4)`, and `created_at` / `updated_at` as `DateTime(timezone=True)`

#### Scenario: Position model upgrade
- **WHEN** the `Position` model is loaded
- **THEN** it MUST have: `user_id` UUID FK, `occ_symbol` VARCHAR(32), `net_quantity` INT (positive=long, negative=short), `average_cost` as `Numeric(12,4)`, `realized_pnl` as `Numeric(14,4)`, and `UNIQUE(user_id, occ_symbol)` constraint

#### Scenario: Watchlist model upgrade
- **WHEN** the `WatchlistTicker` model is loaded
- **THEN** it MUST have: `user_id` UUID FK (replacing ticker-as-PK pattern), `risk_limit_pct` as `Numeric(5,2)` with CHECK constraint 0-100, `auto_trade_enabled` BOOLEAN default FALSE, and `UNIQUE(user_id, ticker)` constraint

---

### Requirement: New Models
New SQLAlchemy models matching DDL tables that don't exist yet.

#### Scenario: User model
- **WHEN** the `User` model is loaded
- **THEN** it MUST define: `user_id` UUID PK, `username` UNIQUE, `email` UNIQUE, `password_hash`, `account_type` Enum (PAPER/LIVE), `cash_balance` Numeric(14,4) with CHECK >= 0, `margin_used` Numeric(14,4) with CHECK >= 0

#### Scenario: UserBrokerCredentials model
- **WHEN** the `UserBrokerCredentials` model is loaded
- **THEN** it MUST define: `user_id` UUID FK UNIQUE, `broker_name`, `api_key`, `api_secret_encrypted` (never exposed in API responses), `webhook_tokens_encrypted` JSONB

#### Scenario: OrderLeg model
- **WHEN** the `OrderLeg` model is loaded
- **THEN** it MUST define: `order_id` FK to `orders_master`, `occ_symbol` VARCHAR(32), `action` Enum (BUY/SELL), `right_type` Enum (CALL/PUT), `strike_price` Numeric(12,4), `expiration_date` DATE, `entry_greeks` JSONB

---

### Requirement: Auto-Migration Compatibility

#### Scenario: New model added
- **WHEN** a new model file is created and imported in `models/__init__.py`
- **THEN** `auto_migrate.ensure_tables()` creates the table automatically on next API restart

#### Scenario: Column added to existing model
- **WHEN** a new column is added to an existing model definition
- **THEN** `auto_migrate.ensure_tables()` detects the missing column and issues `ALTER TABLE ADD COLUMN` on startup
