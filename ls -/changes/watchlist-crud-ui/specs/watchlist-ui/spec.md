## ADDED Requirements

### Requirement: List all watchlist tickers
The system SHALL display all tickers in the watchlist (both active and inactive) in a glassmorphism data table on the settings page. Each row MUST show: ticker name, options support badge, liquidity score, active toggle, and delete action.

#### Scenario: Page load with existing tickers
- **WHEN** user navigates to the settings page
- **THEN** system fetches `GET /api/v1/settings/watchlist` and renders all tickers in the data table

#### Scenario: Empty watchlist
- **WHEN** the watchlist has zero tickers
- **THEN** system displays an empty state message: "当前监控池为空，请在上方添加您的核心关注标的"

### Requirement: Add a ticker to the watchlist
The system SHALL provide a Quick Add Bar with an input field and submit button. The system MUST validate the ticker format (uppercase, 1-6 chars), call `POST /api/v1/settings/watchlist`, and insert the new ticker into the table without full page reload.

#### Scenario: Add valid ticker
- **WHEN** user types "TSLA" and clicks "添加至监控"
- **THEN** system calls POST with `{ "ticker": "TSLA" }`, shows loading animation, and inserts the new ticker row into the table on success

#### Scenario: Add duplicate ticker
- **WHEN** user adds a ticker that already exists
- **THEN** system re-activates it and shows toast: "{ticker} already exists, re-activated"

#### Scenario: Add ticker without options support
- **WHEN** the backend determines `supports_options = false`
- **THEN** system shows a red toast: "该标的不支持期权交易" and the ticker is still added but without the OPT badge

### Requirement: Toggle ticker active state
The system SHALL provide a CSS toggle switch for each ticker. Clicking the switch MUST call `PUT /api/v1/settings/watchlist/{ticker}/toggle` and update the visual state without re-fetching the full list.

#### Scenario: Deactivate an active ticker
- **WHEN** user clicks the toggle switch on an active ticker
- **THEN** system sends PUT toggle request, switch transitions to gray `#374151`, and the ticker is excluded from future scans

#### Scenario: Reactivate an inactive ticker
- **WHEN** user clicks the toggle switch on an inactive ticker
- **THEN** system sends PUT toggle request, switch transitions to cyan `#06b6d4`, and the ticker is included in future scans

#### Scenario: Prevent double-click during toggle
- **WHEN** a toggle request is in-flight
- **THEN** the switch MUST be disabled until the response arrives

### Requirement: Inline edit liquidity score
The system SHALL allow inline editing of `min_liquidity_score` by clicking on the score value. The system MUST display an `<input type="number">` on click, and call `PUT /api/v1/settings/watchlist/{ticker}` on blur or Enter.

#### Scenario: Edit liquidity score
- **WHEN** user clicks the score value "0.5"
- **THEN** system replaces the text with an input field pre-filled with "0.5"
- **WHEN** user changes to "0.7" and presses Enter or clicks away
- **THEN** system calls PUT with `{ "min_liquidity_score": 0.7 }` and updates the display

#### Scenario: Cancel edit
- **WHEN** user presses Escape during inline edit
- **THEN** system reverts to the original value without calling the API

### Requirement: Delete a ticker from the watchlist
The system SHALL provide a delete action (trash icon) for each ticker. Clicking MUST show a confirmation prompt before calling `DELETE /api/v1/settings/watchlist/{ticker}`.

#### Scenario: Confirm deletion
- **WHEN** user clicks the trash icon and confirms
- **THEN** system calls DELETE, removes the row with a fade-out animation, and shows success toast

#### Scenario: Cancel deletion
- **WHEN** user clicks the trash icon and cancels the confirmation
- **THEN** no API call is made and the row remains

### Requirement: Options support badge
The system SHALL display a green `OPT` micro-badge next to tickers where `supports_options = true`. Tickers without options support MUST NOT show the badge.

#### Scenario: Ticker with options
- **WHEN** a ticker has `supports_options = true`
- **THEN** a green `OPT` badge appears next to the ticker name

#### Scenario: Ticker without options
- **WHEN** a ticker has `supports_options = false`
- **THEN** no badge is shown

### Requirement: Backend watchlist persistence
The system SHALL persist watchlist data in the `watchlist_tickers` PostgreSQL table. All CRUD operations MUST read from and write to this table, not in-memory storage.

#### Scenario: Data survives restart
- **WHEN** the API container is restarted
- **THEN** all previously added tickers are still present in the watchlist

### Requirement: Strategy engine reads active tickers from DB
The `/dashboard/scan` endpoint SHALL query the `watchlist_tickers` table for `is_active = true` tickers instead of using a hardcoded list.

#### Scenario: Scan uses DB pool
- **WHEN** `/dashboard/scan` is called
- **THEN** it queries active tickers from DB and scans only those
