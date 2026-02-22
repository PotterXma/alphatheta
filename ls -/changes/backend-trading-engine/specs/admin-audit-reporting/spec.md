## ADDED Requirements

### Requirement: Immutable audit trail
All Kill Switch activations, state machine transitions, API key modifications, and risk rejections SHALL be written to `audit_logs` table. Audit log rows SHALL be append-only (no UPDATE/DELETE permitted at application level).

#### Scenario: Kill switch audit
- **WHEN** kill switch is toggled
- **THEN** audit log entry: severity=CRITICAL, source=admin, message with reason and operator

#### Scenario: Risk rejection audit
- **WHEN** risk engine rejects a trade
- **THEN** audit log: severity=WARN, source=risk_engine, full proposal as metadata JSON

### Requirement: Executive value reporting
The service SHALL auto-generate daily/weekly summary reports showing: total risk rejections (and estimated avoided loss), total rolls executed (and premium collected), total orders processed, system uptime, kill switch activations.

#### Scenario: Daily report generation
- **WHEN** market closes at 16:00 EST
- **THEN** system SHALL aggregate today's metrics and generate a report accessible at `GET /api/v1/admin/reports/daily`

#### Scenario: Report includes value metrics
- **WHEN** daily report is generated after 3 risk rejections and 2 auto-rolls
- **THEN** report SHALL include `risk_rejections: 3`, `estimated_loss_avoided: $X`, `rolls_executed: 2`, `premium_collected: $Y`

### Requirement: API key vault with Fernet encryption
Broker API keys stored encrypted (Fernet symmetric) in PostgreSQL. Decrypted only in-memory for broker adapter. Support read-only and read-write modes.

#### Scenario: Read-only mode enforcement
- **WHEN** API key mode is read-only AND order submission attempted
- **THEN** broker adapter SHALL refuse with error `"API key is in read-only mode"`

### Requirement: Health check with subsystem status
`GET /api/v1/health` SHALL return status of: PostgreSQL, TimescaleDB, Redis, broker API, NTP sync, kill switch state, environment mode.

#### Scenario: Degraded health
- **WHEN** broker API unreachable
- **THEN** return 200 with `{ status: "degraded", broker: "down", env: "paper" }`

### Requirement: System log WebSocket streaming
Audit logs SHALL be pushed in real-time to WebSocket `system_logs` channel. REST `GET /api/v1/admin/logs` for paginated historical access.

#### Scenario: Real-time log push
- **WHEN** new audit log entry created
- **THEN** pushed to all `system_logs` subscribers within 1s

### Requirement: Admin REST endpoints
`POST /api/v1/admin/api-keys`, `GET /api/v1/admin/api-keys` (masked), `DELETE /api/v1/admin/api-keys/{id}`, `POST /api/v1/admin/kill-switch`, `GET /api/v1/admin/kill-switch`, `GET /api/v1/admin/logs`, `GET /api/v1/admin/reports/daily`.

#### Scenario: Masked key listing
- **WHEN** GET `/api/v1/admin/api-keys`
- **THEN** return keys with `key: "****-XXXX"` (last 4 visible)
