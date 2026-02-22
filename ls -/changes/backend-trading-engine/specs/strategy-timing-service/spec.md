## ADDED Requirements

### Requirement: 4-scene decision tree with VIX override
Stateless function evaluating RSI-14, VIX, position state → single recommended action. VIX > 35 overrides all with Hold.

#### Scenario: Scene A — Oversold, no position, RSI < 40
- **WHEN** RSI=28, position=cash
- **THEN** return `action_type: "Sell Put ONLY"`

#### Scenario: Scene B — Overbought, has position, RSI > 60
- **WHEN** RSI=72, position=100 shares
- **THEN** return `action_type: "Sell Call ONLY"`

### Requirement: Corporate actions parser (dividends, splits)
The service SHALL parse external corporate action feeds (ex-dividend dates, stock splits) and dynamically adjust pre-set strike prices. On a 2:1 split, all pending order strikes SHALL be halved and quantities doubled.

#### Scenario: Stock split adjustment
- **WHEN** a 2:1 split is detected for AAPL AND pending order has strike=$200
- **THEN** system SHALL adjust to strike=$100, quantity×2, and create audit log

#### Scenario: Ex-dividend date warning
- **WHEN** DTE overlaps with ex-dividend date for a covered call
- **THEN** strategy SHALL add `early_assignment_risk: true` flag and adjust playbook

### Requirement: Pin Risk / DTE=0 expiration auto-close
On expiration day (DTE=0), the service SHALL automatically close or roll any at-the-money options positions to avoid pin risk and unwanted assignment. Threshold: |delta| > 0.40 on expiration day triggers forced action.

#### Scenario: Auto-close on DTE=0
- **WHEN** DTE=0 AND option position has |delta| > 0.40
- **THEN** system SHALL generate a "close position" order and push alert to `system_logs` WebSocket

#### Scenario: DTE=0 but safe delta
- **WHEN** DTE=0 AND option position has |delta| < 0.20
- **THEN** system SHALL allow expiry without action and log "safe expiry"

### Requirement: Sandbox projection calculator
Stateless endpoint for strategy projections: Net Cost, Break-even, Max Profit, Annualized Yield.

#### Scenario: Covered call projection
- **WHEN** POST `/api/v1/strategy/project` with covered_call params
- **THEN** return computed `net_cost`, `break_even`, `max_profit`, `annualized_yield`

### Requirement: REST endpoints
- `POST /api/v1/strategy/timing` — timing decision
- `POST /api/v1/strategy/project` — sandbox projection

#### Scenario: Timing endpoint
- **WHEN** POST with market context
- **THEN** 200 with `action_type`, `scene_label`, `scene_factors`, `execution_details`
