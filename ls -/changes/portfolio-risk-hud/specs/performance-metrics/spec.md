## ADDED Requirements

### Requirement: Win rate display
The performance metrics grid SHALL display the portfolio win rate as a percentage. Values above 50% SHALL be styled green, at or below 50% SHALL be styled red.

#### Scenario: High win rate
- **WHEN** win rate is 78.5%
- **THEN** the display shows "78.5%" in green with label "Win Rate"

### Requirement: Max drawdown display
The performance metrics grid SHALL display the maximum portfolio drawdown as a negative percentage. The value SHALL always be styled in danger red to emphasize risk. This is the most critical risk metric.

#### Scenario: Drawdown display
- **WHEN** max drawdown is -12.4%
- **THEN** the display shows "-12.4%" in red with label "Max Drawdown"

### Requirement: Profit factor display
The performance metrics grid SHALL display the profit factor (gross profit / gross loss ratio). Values above 1.0 SHALL be styled green, at or below 1.0 SHALL be styled red.

#### Scenario: Profitable factor
- **WHEN** profit factor is 1.85
- **THEN** the display shows "1.85" in green with label "Profit Factor"

### Requirement: Sharpe ratio display
The performance metrics grid SHALL display the Sharpe ratio. Values above 1.0 SHALL be styled cyan, at or below 1.0 SHALL be styled amber as a warning.

#### Scenario: Good Sharpe ratio
- **WHEN** Sharpe ratio is 1.42
- **THEN** the display shows "1.42" in cyan with label "Sharpe Ratio"

### Requirement: Grid layout below equity curve
The `.perf-metrics-grid` container SHALL be positioned immediately below the equity curve chart within the `.report-card`. It SHALL use a 4-column CSS grid layout. Each cell SHALL be a compact glassmorphic card with label above and value below in monospace font.

#### Scenario: Grid renders below chart
- **WHEN** the lifecycle view is rendered
- **THEN** four metric cards appear in a single row below the equity curve chart
