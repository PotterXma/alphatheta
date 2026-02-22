## ADDED Requirements

### Requirement: Status beacon with CSS animation
The bot telemetry card SHALL display an animated status beacon indicating the automation engine state. The beacon SHALL support three states:
- `scanning` — cyan pulsing glow animation (engine actively scanning)
- `halted` — red pulsing glow animation (circuit breaker triggered)
- `standby` — amber static glow (engine idle, awaiting triggers)

The animation SHALL use CSS `@keyframes` with `box-shadow` expansion. The animation SHALL be disabled when `prefers-reduced-motion: reduce` is active.

#### Scenario: Scanning state
- **WHEN** bot status is "scanning"
- **THEN** the beacon displays a cyan circle with a pulsing glow animation and the label "扫描中"

#### Scenario: Halted state
- **WHEN** bot status is "halted"
- **THEN** the beacon displays a red circle with a pulsing glow animation and the label "熔断"

#### Scenario: Standby state
- **WHEN** bot status is "standby"
- **THEN** the beacon displays an amber static circle and the label "待机"

### Requirement: Today's executed orders count
The bot telemetry card SHALL display the number of orders executed today as a numeric indicator with the label "今日执行指令".

#### Scenario: Orders display
- **WHEN** today's orders count is 3
- **THEN** the display shows "3 笔" in monospace font

### Requirement: API latency indicator
The bot telemetry card SHALL display the current API round-trip latency in milliseconds.

#### Scenario: Normal latency
- **WHEN** API latency is 45ms
- **THEN** the display shows "45ms" in monospace font with cyan color

### Requirement: Refactored card layout
The existing `.report-metrics` area within `.report-card` SHALL be refactored into a `.bot-telemetry` card containing the beacon, status label, orders count, and API latency in a compact horizontal layout.

#### Scenario: Card structure
- **WHEN** the lifecycle view is rendered
- **THEN** the bot telemetry card replaces the old report-metrics div with beacon on the left and metrics on the right
