## ADDED Requirements

### Requirement: Decision tree evaluates 4 market scenarios
The system SHALL implement a pure function `evaluateTimingDecision()` that accepts market context and signal data, and returns a single recommended action based on 4 mutually exclusive scenarios evaluated in priority order.

#### Scenario: VIX extreme fear override (Priority 0)
- **WHEN** VIX > 35
- **THEN** system SHALL return `action_type: "Hold"` with rationale "VIX极端恐慌，暂停一切卖出策略" regardless of RSI or position state

#### Scenario: Oversold with no position (Scene A, Priority 1)
- **WHEN** RSI-14 < 40 AND current_position is "0 (cash)"
- **THEN** system SHALL return `action_type: "Sell Put ONLY"` or `"Buy Stock ONLY"` with execution details recommending cash-secured put or stock purchase at current price. System SHALL NOT recommend selling calls.

#### Scenario: Overbought with existing position (Scene B, Priority 2)
- **WHEN** RSI-14 > 60 AND current_position includes shares (e.g., "100 shares")
- **THEN** system SHALL return `action_type: "Sell Call ONLY"` targeting the call candidate strike/premium to harvest elevated premium

#### Scenario: Overbought with no position (Scene C, Priority 3)
- **WHEN** RSI-14 > 60 AND current_position is "0 (cash)"
- **THEN** system SHALL return `action_type: "Hold"` with rationale advising against buying stock at overbought levels. MAY suggest selling deep OTM put as alternative.

#### Scenario: Range-bound with no position (Scene D, Priority 4)
- **WHEN** RSI-14 between 40-60 AND current_position is "0 (cash)"
- **THEN** system SHALL return `action_type: "Buy-Write"` recommending simultaneous stock purchase + covered call sale

#### Scenario: Range-bound with existing position (Fallback)
- **WHEN** RSI-14 between 40-60 AND current_position includes shares
- **THEN** system SHALL return `action_type: "Hold"` waiting for more extreme RSI signal

### Requirement: Extended mock data fields
The system SHALL extend `MOCK_DATA.marketContext` with the following new fields: `rsi_14` (number), `distance_to_sma200` (percentage), `current_position` (string), `available_cash` (number), `put_strike` (number), `put_premium` (number).

#### Scenario: Default mock values reflect range-bound market
- **WHEN** application loads with default mock data
- **THEN** `rsi_14` SHALL be 55, `distance_to_sma200` SHALL be 9.71, `current_position` SHALL be "100 shares", `available_cash` SHALL be 45000, `put_strike` SHALL be 505, `put_premium` SHALL be 3.80

### Requirement: Decision tree executes before risk evaluator
The system SHALL call `evaluateTimingDecision()` before `evaluateTradeProposal()` within the `renderSignal()` flow. The timing decision's recommended action SHALL be passed to the risk evaluator for compliance checking.

#### Scenario: Timing recommends Sell Put but risk rejects
- **WHEN** timing engine recommends "Sell Put ONLY" AND risk evaluator rejects (e.g., margin > 60%)
- **THEN** UI SHALL display the timing recommendation badge AND the risk rejection badge, clearly showing both layers of evaluation

### Requirement: Output JSON structure
The function SHALL return a JSON object matching the schema: `{ action_type, target_ticker, execution_details, scene_label, scene_factors: { rsi, vix, position } }`.

#### Scenario: Complete output for Scene A
- **WHEN** RSI=28, VIX=22, position="0 (cash)"
- **THEN** returned object SHALL contain `action_type: "Sell Put ONLY"`, `scene_label: "A"`, and `scene_factors` with all 3 values populated
