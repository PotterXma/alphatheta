## ADDED Requirements

### Requirement: Scanner Loop Lifecycle
Standalone asyncio process that wakes on schedule during market hours.

#### Scenario: Market hours wake cycle
- **WHEN** the current time is between 09:30-16:00 EST on a NYSE trading day
- **THEN** the scanner wakes every 15 minutes, fetches the deduplicated global watchlist, and runs the two-stage filter

#### Scenario: Off-hours behavior
- **WHEN** the current time is outside market hours or on a non-trading day
- **THEN** the scanner sleeps until the next market open (calculated via `exchange_calendars` XNYS)

#### Scenario: Heartbeat
- **WHEN** each scan cycle completes (success or failure)
- **THEN** a heartbeat timestamp is written to Redis key `scanner:heartbeat` with 30-minute TTL

---

### Requirement: Two-Stage Filtering Pipeline

#### Scenario: Stage 1 — RSI pre-filter
- **WHEN** a ticker from the global watchlist is evaluated
- **THEN** its 14-day RSI is calculated. Only tickers with RSI < 35 advance to Stage 2

#### Scenario: Stage 2 — LEAPS option chain deep dive
- **WHEN** a ticker passes Stage 1
- **THEN** the scanner fetches its option chain (throttled with `random.uniform(1.5, 3.0)` second delay between API calls), and filters for LEAPS puts with: DTE > 180, IV Rank < 30th percentile, bid-ask spread < 5%, open interest > 100

#### Scenario: Signal found
- **WHEN** a qualifying LEAPS option is found
- **THEN** a signal payload is constructed with: `ticker`, `occ_symbol`, `strategy_name`, `strike_price`, `expiration_date`, `iv_rank`, `delta`, `estimated_premium`, `rsi`, `timestamp`

---

### Requirement: API Throttling & Error Handling

#### Scenario: Rate limit hit
- **WHEN** the upstream data API returns 429 Too Many Requests
- **THEN** the scanner backs off exponentially (base 30s, max 5min) and logs a WARNING

#### Scenario: API timeout
- **WHEN** a data API call exceeds 30 seconds
- **THEN** the ticker is skipped for this cycle with an ERROR log, and the scanner continues to the next ticker

#### Scenario: Unhandled exception
- **WHEN** an unexpected exception occurs during a scan cycle
- **THEN** the error is logged with full traceback, the cycle is abandoned, and the scanner sleeps until the next scheduled wake
