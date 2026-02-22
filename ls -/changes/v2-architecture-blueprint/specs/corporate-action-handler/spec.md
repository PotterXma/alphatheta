## ADDED Requirements

### Requirement: Stock Split Handling
Automatic position adjustment when a stock splits.

#### Scenario: Forward split (e.g., 4:1)
- **WHEN** a stock split is detected for a ticker in any user's positions
- **THEN** for each affected `user_positions` row: `net_quantity *= split_ratio`, `strike_price /= split_ratio`, `average_cost /= split_ratio`, and `occ_symbol` is regenerated with the new strike. An audit log entry is created.

#### Scenario: Reverse split (e.g., 1:10)
- **WHEN** a reverse split is detected
- **THEN** quantities are divided (rounded down), strikes are multiplied, and fractional shares are settled to cash at market price

---

### Requirement: Dividend Ex-Date Monitoring

#### Scenario: Early assignment radar
- **WHEN** a user holds a short call position (net_quantity < 0) AND the underlying's ex-dividend date is within 3 calendar days AND the short call is ITM (underlying_price > strike_price)
- **THEN** a CRITICAL alert is pushed to the user via WebSocket and webhook with message: "⚠️ Early assignment risk: {ticker} ex-div {date}, your short {strike}C is ITM by ${amount}"

#### Scenario: No risk detected
- **WHEN** the daily check runs and no short calls meet the early assignment criteria
- **THEN** no alert is generated (silent pass)

---

### Requirement: Daily Corporate Action Poll

#### Scenario: Scheduled execution
- **WHEN** the system clock reaches 06:00 EST on a business day
- **THEN** the corporate action checker queries the data API for splits and dividends affecting tickers in any user's watchlist or positions, for the next 7 calendar days

#### Scenario: Data API failure
- **WHEN** the corporate action API call fails
- **THEN** the failure is logged as ERROR, and the check is retried at 06:30 EST. After 3 failures, an admin alert is sent.
