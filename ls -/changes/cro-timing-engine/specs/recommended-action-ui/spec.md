## ADDED Requirements

### Requirement: Recommended action panel in Signal view
The system SHALL display a "推荐操作" (Recommended Action) panel in the Signal view, positioned above the CRO approval badge. The panel SHALL show the action type, target ticker, execution details, and scene factors.

#### Scenario: Panel displays Buy-Write recommendation
- **WHEN** timing engine returns `action_type: "Buy-Write"` for ticker SPY
- **THEN** panel SHALL display an emerald-colored badge with text "Buy-Write", ticker "SPY", and execution details describing simultaneous stock purchase + call sale

#### Scenario: Panel displays Hold recommendation
- **WHEN** timing engine returns `action_type: "Hold"`
- **THEN** panel SHALL display a gray-colored badge with text "Hold / 观望", and execution details explaining why (e.g., "VIX > 35" or "RSI overbought, no position")

### Requirement: Action type color coding
The system SHALL apply distinct color coding to the action type badge: emerald/green for Buy Stock and Buy-Write, cyan for Sell Call, amber for Sell Put, gray for Hold.

#### Scenario: Sell Put uses amber accent
- **WHEN** recommended action is "Sell Put ONLY"
- **THEN** action badge SHALL use `var(--color-warn)` (amber) background accent

#### Scenario: Hold uses muted gray
- **WHEN** recommended action is "Hold"
- **THEN** action badge SHALL use muted gray background with reduced opacity

### Requirement: Scene factors display
The panel SHALL display the key factors that drove the decision: current RSI value, VIX level, and position state, formatted as compact inline badges or tags.

#### Scenario: Factors show RSI and VIX values
- **WHEN** timing decision is made with RSI=55, VIX=18.5, position="100 shares"
- **THEN** panel SHALL display "RSI 55", "VIX 18.5", "已持仓 100股" as factor badges

### Requirement: i18n coverage for all new UI text
The system SHALL add i18n keys to both `zh` and `en` dictionaries for: panel title, all 5 action type labels, scene factor labels, and execution detail templates.

#### Scenario: Language toggle updates action panel
- **WHEN** user toggles language from Chinese to English
- **THEN** all action panel text SHALL update: "推荐操作" → "Recommended Action", "观望" → "Hold", "已持仓" → "Holding", etc.

### Requirement: Panel hidden when timing engine returns null
The system SHALL hide the recommended action panel if `evaluateTimingDecision()` returns null or undefined (defensive fallback).

#### Scenario: Graceful handling of missing timing data
- **WHEN** `evaluateTimingDecision()` throws or returns null
- **THEN** recommended action panel SHALL be hidden and CRO evaluation SHALL proceed with default behavior
