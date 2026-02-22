## ADDED Requirements

### Requirement: Sandbox auto-fills real market data on ticker change
The system SHALL automatically populate the Sandbox form with real-time data when `globalActiveTicker` changes: current spot price, ATM strike, and ATM option premium.

#### Scenario: Ticker changes to AMD
- **WHEN** `globalActiveTicker` changes to "AMD"
- **THEN** system fetches AMD option chain, fills Spot Price input with current price, ATM Strike with nearest strike, and Premium with mid-price of ATM option

#### Scenario: Option chain unavailable
- **WHEN** `globalActiveTicker` changes to a ticker with no options chain
- **THEN** system fills Spot Price with current price but leaves Strike and Premium as 0 with a toast warning

### Requirement: Payoff diagram container is present
The system SHALL render a `<div id="payoff-chart-container">` in the Sandbox page with ECharts initialization skeleton code.

#### Scenario: Container exists on page load
- **WHEN** user navigates to the Sandbox page
- **THEN** a chart container element exists with id "payoff-chart-container" and ECharts instance is initialized (even if empty)

### Requirement: Sandbox respects global ticker on initial load
The system SHALL read `globalActiveTicker` on Sandbox page initialization and auto-fill data for that ticker.

#### Scenario: Navigate to Sandbox with pre-set ticker
- **WHEN** `globalActiveTicker` is "NVDA" and user navigates to Sandbox
- **THEN** Sandbox immediately fetches NVDA data and fills the form, without waiting for a ticker-changed event
