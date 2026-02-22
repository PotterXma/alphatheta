## ADDED Requirements

### Requirement: On-demand throttled quote subscription
The service SHALL implement an on-demand subscription mechanism for OPRA option data, subscribing only to tickers and strikes currently active in the sandbox or decision tree. Idle tickers SHALL be unsubscribed after 5 minutes of inactivity to control data costs.

#### Scenario: Subscribe on sandbox activation
- **WHEN** sandbox requests options chain for SPY $525 Call
- **THEN** service SHALL subscribe to SPY option quotes for the relevant strike range and cache results

#### Scenario: Unsubscribe idle tickers
- **WHEN** no requests for ticker QQQ in 5 minutes
- **THEN** service SHALL unsubscribe from QQQ option feed and remove cached data

### Requirement: HTTP 429 rate limit handling with circuit breaker
The service SHALL implement exponential backoff retry (3x, base 1s) and circuit breaker (30s cooldown after 5 consecutive 429s) for all broker API calls. During circuit breaker cooldown, requests SHALL be queued locally.

#### Scenario: Broker rate limited
- **WHEN** broker API returns 429 three times consecutively
- **THEN** service SHALL retry with exponential backoff (1s, 2s, 4s) and log each retry to audit

#### Scenario: Circuit breaker activation
- **WHEN** 5 consecutive 429 errors occur within 60 seconds
- **THEN** circuit breaker SHALL open for 30s, queuing requests locally, and push WARN to system_logs WebSocket channel

### Requirement: Market calendar middleware with NTP
The service SHALL load the US stock exchange calendar (`exchange_calendars` library) at startup and enforce trading hours on all mutating operations. System clock SHALL be validated against NTP with < 100ms tolerance.

#### Scenario: Request during market close
- **WHEN** a POST to `/api/v1/orders` arrives on a weekend or US holiday
- **THEN** middleware SHALL return 409 with `{ error: "Market closed", next_open: "2026-02-23T09:30:00-05:00" }`

#### Scenario: Early close handling (e.g., Christmas Eve)
- **WHEN** current date is a half-day session (close at 13:00 EST) and time is 13:01 EST
- **THEN** middleware SHALL treat market as closed and suspend decision tree execution

### Requirement: RSI-14 and SMA200 calculation with Wilder smoothing
The service SHALL compute RSI-14 using the standard Wilder smoothing method and SMA200 distance as percentage from current price. Results SHALL be cached in Redis at `market:indicators:{ticker}` with 60s TTL.

#### Scenario: RSI calculation accuracy
- **WHEN** 15+ daily closes are available
- **THEN** RSI-14 SHALL be calculated and return a value between 0-100 matching Wilder's formula

### Requirement: Tick and Greeks storage in TimescaleDB
The service SHALL store raw ticks and Greeks snapshots in TimescaleDB hypertables with automatic time-based partitioning (7-day chunks). Data retention SHALL be configurable (default 90 days).

#### Scenario: Tick data insertion
- **WHEN** a new tick arrives for SPY
- **THEN** it SHALL be inserted into `tick_data` hypertable with columns: `time`, `ticker`, `bid`, `ask`, `last`, `volume`

### Requirement: WebSocket market feed and REST endpoint
The service SHALL expose WebSocket channel `market` pushing real-time `marketContext` updates, and REST `GET /api/v1/market/{ticker}` for on-demand queries.

#### Scenario: WebSocket push on tick update
- **WHEN** a new tick is cached for SPY
- **THEN** all clients subscribed to `market` channel SHALL receive the updated `marketContext` JSON
