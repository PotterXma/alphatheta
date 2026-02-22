## ADDED Requirements

### Requirement: Top picks endpoint returns 3 recommendations
The system SHALL expose `GET /api/v1/strategy/top-picks` that returns up to 3 highest-value tickers from the active watchlist, ranked by premium yield or IV Rank descending.

#### Scenario: Successful top picks with 3+ eligible tickers
- **WHEN** the watchlist has 6 active tickers and 4 pass earnings filter
- **THEN** the endpoint returns the top 3 by premium yield in descending order, each with ticker, score, current_price, and atm_premium fields

#### Scenario: Fewer than 3 eligible tickers
- **WHEN** only 2 tickers pass the earnings filter
- **THEN** the endpoint returns those 2 tickers (no padding with ineligible ones)

### Requirement: Earnings blackout filter excludes tickers within 14 days of earnings
The system SHALL fetch `earningsDates` from yfinance for each candidate ticker and MUST exclude any ticker whose next earnings date falls within the next 14 calendar days.

#### Scenario: Ticker with earnings in 10 days
- **WHEN** AAPL has earnings in 10 days
- **THEN** AAPL is excluded from top picks results

#### Scenario: Ticker with no earnings data
- **WHEN** yfinance returns empty earningsDates for a ticker
- **THEN** the ticker is treated as "safe" (not in blackout window) and remains eligible

#### Scenario: Ticker with earnings in 20 days
- **WHEN** MSFT has earnings in 20 days
- **THEN** MSFT remains eligible for top picks
