## ADDED Requirements

### Requirement: Server-side 7 kill switch rules
The risk engine SHALL implement all 7 kill switch rules server-side, matching front-end CRO v2 logic. Rules evaluated sequentially; first trigger halts with rejection.

#### Scenario: Rule 1 — Data staleness
- **WHEN** `data_latency_seconds` > 15
- **THEN** reject with `[Rule 1·Stale Data]`

#### Scenario: All 7 rules pass
- **WHEN** no rule triggered
- **THEN** return `is_approved: true` with execution plan and playbooks

### Requirement: Paper / Live environment isolation
The risk engine SHALL enforce strict environment isolation. Paper mode SHALL use `PaperBrokerAdapter` (local simulation) and paper-prefixed DB tables. Live mode SHALL use the real broker adapter. API responses SHALL include `X-Env-Mode` header.

#### Scenario: Paper mode blocks live broker calls
- **WHEN** `ENV_MODE=paper` AND risk engine approves a trade
- **THEN** order SHALL be routed to `PaperBrokerAdapter` which simulates fills locally without hitting real broker API

#### Scenario: Environment mismatch rejection
- **WHEN** a request arrives with `X-Env-Mode: live` but server is configured as paper
- **THEN** system SHALL return 403 with `{ error: "Environment mismatch" }`

### Requirement: Kill switch middleware with dual persistence
Kill switch state SHALL be dual-written to Redis (`system:kill_switch:{env}`) and PostgreSQL. On startup, PG state SHALL be restored to Redis. All mutating API calls (POST/PUT/DELETE on orders) SHALL be blocked when kill switch is active.

#### Scenario: Kill switch blocks order in live mode
- **WHEN** kill switch is active for `live` env AND POST `/api/v1/orders` arrives
- **THEN** return 503 with `{ error: "Kill switch active" }` and log to audit

### Requirement: Execution plan with Limit_Price_Chaser
For approved trades, generate `Limit_Price_Chaser` plan with `starting_limit_price` (mid) and `floor_limit_price` (bid + spread×0.2), plus gross/net yield.

#### Scenario: Plan generation
- **WHEN** trade approved with bid=5.0, ask=5.4, strike=525, dte=43, tax_drag=0.30
- **THEN** starting_limit=5.20, floor_limit=5.08, gross_yield and net_yield calculated

### Requirement: REST endpoint POST /api/v1/risk/evaluate
Accept trade proposal body, return full CRO assessment with playbooks and rationale.

#### Scenario: Evaluate and return
- **WHEN** valid proposal submitted
- **THEN** 200 with `is_approved`, `rejection_reason`, `execution_plan`, `scenario_playbooks`, `ui_rationale`
