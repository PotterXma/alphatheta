## ADDED Requirements

### Requirement: Order state machine with idempotency
FSM states: Draft, Pending, Filled, PartialFill, Rejected, Cancelled. All `submit()` calls SHALL carry `Idempotency-Key` (UUID v4). Redis SHALL store `idempotency:{key}` with 24h TTL; duplicate submissions SHALL return cached original response.

#### Scenario: Idempotent duplicate submission
- **WHEN** same `Idempotency-Key` is submitted twice
- **THEN** second call SHALL return the cached response from the first call without creating a new order or calling broker API

#### Scenario: Valid state transition
- **WHEN** `submit()` on Draft order
- **THEN** transition to Pending, call broker adapter, log audit entry

#### Scenario: Invalid state transition
- **WHEN** transition Filled → Draft attempted
- **THEN** raise `InvalidStateTransition`, log ERROR audit

### Requirement: Independent reconciliation daemon
A separate process (K8s CronJob or sidecar) SHALL periodically (every 60s during market hours) fetch broker's real positions and open orders, compare against local DB, and flag discrepancies.

#### Scenario: Missed fill detection
- **WHEN** broker shows order #123 as filled but local status is Pending
- **THEN** daemon SHALL update local to Filled, populate fill details, create RECONCILIATION audit log, push CRITICAL alert

#### Scenario: Phantom order detection
- **WHEN** local DB has Pending order but broker has no record
- **THEN** daemon SHALL mark as Rejected with reason `broker_not_found`, create CRITICAL audit log

### Requirement: Position tracking with atomic updates
Positions table SHALL be updated atomically (within same DB transaction) on order fills. Position fields: ticker, quantity, avg_cost_basis, current_value, unrealized_pnl.

#### Scenario: First position creation
- **WHEN** 100 shares of SPY filled at $505
- **THEN** create position: quantity=100, avg_cost_basis=505.00

### Requirement: Roll calculation engine
Calculate Roll Up (strike × 1.05), Roll Down (strike × 0.90), Roll Out (+30 DTE). Return estimated credit/debit for each roll option.

#### Scenario: Roll Up
- **WHEN** roll request for $525 call
- **THEN** return new_strike=$551, new_expiration=current+30d, estimated_credit

### Requirement: Broker adapter with IBKR support
Abstract `BrokerAdapter` ABC with methods: `submit_order`, `cancel_order`, `get_positions`, `get_quote`, `get_option_chain`. Implement `TradierAdapter` first, `IBKRAdapter` second.

#### Scenario: Broker adapter swap
- **WHEN** config switches from tradier to ibkr
- **THEN** DI SHALL inject IBKRAdapter without code changes to services

### Requirement: REST endpoints for OMS
`POST /api/v1/orders`, `GET /api/v1/orders`, `POST /api/v1/orders/{id}/submit` (requires Idempotency-Key header), `POST /api/v1/orders/{id}/cancel`, `POST /api/v1/orders/roll`, `GET /api/v1/positions`.

#### Scenario: Submit with idempotency
- **WHEN** POST `/api/v1/orders/{id}/submit` without `Idempotency-Key` header
- **THEN** return 400 with `{ error: "Idempotency-Key header required" }`
