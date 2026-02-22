## ADDED Requirements

### Requirement: Bullish surge playbook
For approved trades, the evaluator SHALL generate a bullish scenario playbook describing the Roll Up/Out strategy when the underlying surges +15%.

#### Scenario: Covered call bullish response
- **WHEN** an approved Covered Call trade faces a 15% price increase
- **THEN** the playbook SHALL recommend rolling up the strike or rolling out to a later expiry to capture additional upside

### Requirement: Bearish crash playbook
For approved trades, the evaluator SHALL generate a bearish scenario playbook describing the Roll Down/Out or defensive strategy when the underlying drops -20%.

#### Scenario: Covered call bearish response
- **WHEN** an approved Covered Call trade faces a 20% price drop
- **THEN** the playbook SHALL recommend rolling down to a lower strike for additional premium income and reducing cost basis

### Requirement: Dynamic playbook text
Playbook text SHALL include specific price levels calculated from the current underlying price (e.g., "+15% target = $581" for SPY at $505).

#### Scenario: Price-specific playbook
- **WHEN** underlying is SPY at $505.20
- **THEN** bullish playbook SHALL reference ~$581 and bearish SHALL reference ~$404
