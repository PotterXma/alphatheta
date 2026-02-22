## ADDED Requirements

### Requirement: AI action instruction panel
The Signal view SHALL display the recommended action, quantity, capital impact, and a glowing execute button.

#### Scenario: Signal renders with mock data
- **WHEN** Signal view is active
- **THEN** the action badge, ticker, strike, expiration, quantity, and capital impact SHALL be rendered

### Requirement: Dynamic button color
Execute button SHALL use emerald green gradient for buy actions and cyan-blue gradient for sell/premium-collection actions.

#### Scenario: Buy action
- **WHEN** the signal involves buying stock
- **THEN** execute button SHALL use emerald green gradient

### Requirement: Rationale panel
A right-column panel SHALL display "AI策略执行理由" as a numbered list of reasons.

#### Scenario: Rationale renders
- **WHEN** `currentSignal.rationale` has 3 items
- **THEN** all 3 SHALL appear as an ordered list in the rationale panel

### Requirement: Halt disables execution
When `isHalted` is true, the execute button SHALL be disabled and greyed out.

#### Scenario: Halted state
- **WHEN** kill switch is active
- **THEN** execute button SHALL be visually disabled and clicks SHALL have no effect
