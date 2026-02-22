## ADDED Requirements

### Requirement: Redis Signal Publishing
Scanner publishes signals to Redis for API consumption.

#### Scenario: Signal publish
- **WHEN** the scanner daemon finds a qualifying LEAPS signal
- **THEN** it publishes a JSON payload to Redis channel `signals:broadcast` and stores the signal in Redis hash `signals:latest:{ticker}` with 24h TTL

#### Scenario: Signal deduplication
- **WHEN** a signal for the same OCC symbol has been published within the last 24 hours
- **THEN** the duplicate signal is suppressed (checked via Redis SET `signals:dedup` with SISMEMBER)

---

### Requirement: WebSocket Signal Delivery
API server subscribes to Redis and pushes to connected frontends.

#### Scenario: WebSocket connection
- **WHEN** a frontend client connects to `ws://api/ws/signals?token=<JWT>`
- **THEN** the server validates the JWT, subscribes to `signals:broadcast`, and filters signals to only tickers in the user's watchlist

#### Scenario: Signal broadcast
- **WHEN** a new signal is received from Redis pub/sub
- **THEN** the API checks if the signal's ticker is in the connected user's watchlist, and if so, pushes the signal JSON to the WebSocket

#### Scenario: Frontend toast rendering
- **WHEN** the frontend receives a signal via WebSocket
- **THEN** a toast notification is displayed with: ticker, strategy name, strike, premium, and a "View in Studio" action button

---

### Requirement: Notification Webhooks

#### Scenario: Webhook delivery
- **WHEN** a signal is found and the user has configured webhook tokens (ServerChan, PushPlus, Bark)
- **THEN** the signal summary is sent via HTTP POST to each configured webhook endpoint (fire-and-forget, max 5s timeout)

#### Scenario: Webhook failure
- **WHEN** a webhook POST fails or times out
- **THEN** the failure is logged but does NOT block signal processing or WebSocket delivery
