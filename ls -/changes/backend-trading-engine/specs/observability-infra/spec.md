## ADDED Requirements

### Requirement: OpenTelemetry distributed tracing
The system SHALL integrate OpenTelemetry SDK with auto-instrumentation for FastAPI, httpx (broker calls), SQLAlchemy, and Redis. Every request SHALL carry a global `TraceID` from WebSocket signal receipt through broker order confirmation.

#### Scenario: Full trace from signal to fill
- **WHEN** a trade signal is received, evaluated by risk engine, and submitted to broker
- **THEN** all spans (risk_evaluate, broker_submit, db_write) SHALL share the same TraceID, viewable in Jaeger/Zipkin

#### Scenario: Custom span for risk evaluation
- **WHEN** risk engine evaluates a proposal
- **THEN** a custom span `risk.evaluate_proposal` SHALL be created with attributes: `rule_count`, `is_approved`, `rejection_rule` (if any)

### Requirement: Prometheus metrics endpoint
The system SHALL expose `/metrics` in Prometheus exposition format with counters and histograms: `api_request_duration_seconds`, `risk_rejections_total` (by rule), `orders_submitted_total` (by status), `reconciliation_mismatches_total`, `broker_api_latency_seconds`, `ws_active_connections`, `kill_switch_activations_total`.

#### Scenario: Metrics scraping
- **WHEN** Prometheus scrapes `/metrics`
- **THEN** response SHALL contain all registered metrics with current values

#### Scenario: Risk rejection counter
- **WHEN** risk engine rejects 5 trades (3 by Rule 7, 2 by Rule 2)
- **THEN** `risk_rejections_total{rule="7"}` SHALL be 3, `risk_rejections_total{rule="2"}` SHALL be 2

### Requirement: K8s deployment manifests
The system SHALL include K8s manifests with: Deployment (2 replicas), Service (ClusterIP), ConfigMap (non-secret config), Liveness probe (`/healthz`), Readiness probe (`/readyz`), resource limits (256Mi-512Mi memory, 250m-500m CPU).

#### Scenario: Liveness probe
- **WHEN** K8s sends GET `/healthz`
- **THEN** return 200 if app process is alive (basic check, no dependency validation)

#### Scenario: Readiness probe
- **WHEN** K8s sends GET `/readyz`
- **THEN** return 200 only if PostgreSQL AND Redis connections are healthy

### Requirement: Graceful shutdown
On SIGTERM, the system SHALL: (1) stop accepting new requests, (2) drain active WebSocket connections with close frame, (3) flush pending DB writes, (4) complete in-flight broker API calls, (5) exit within 30s.

#### Scenario: Pod termination during active WS
- **WHEN** SIGTERM received with 10 active WebSocket connections
- **THEN** all connections SHALL receive close frame with code 1001 (Going Away) before shutdown

### Requirement: Replay engine for CI/CD testing
The system SHALL include a `replay/` module that can inject historical tick data (JSON fixtures) into the market data service, bypassing the broker adapter. Decision tree and risk engine SHALL process replayed data deterministically.

#### Scenario: Replay 2020 COVID crash
- **WHEN** replay runner loads `fixtures/covid_crash_2020.json` with VIX=82 ticks
- **THEN** risk engine SHALL trigger VIX > 35 kill switch, decision tree SHALL return Hold, all outputs SHALL be deterministic across runs

#### Scenario: Replay in CI pipeline
- **WHEN** CI job runs `python3 -m replay.runner --fixture=covid_crash_2020`
- **THEN** process SHALL exit 0 if all assertions pass, exit 1 if any risk/timing logic fails
