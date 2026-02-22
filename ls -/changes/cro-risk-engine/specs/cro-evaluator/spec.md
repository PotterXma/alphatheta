## ADDED Requirements

### Requirement: Trade proposal evaluation function
The system SHALL provide a synchronous `evaluateTradeProposal(proposal, market, account)` function that returns a JSON object with `is_approved`, `rejection_reason`, `execution_plan`, `scenario_playbooks`, and `ui_rationale` fields.

#### Scenario: Approved trade
- **WHEN** a trade proposal passes all 5 kill switch rules and annualized yield is within 7%-20%
- **THEN** `is_approved` SHALL be `true` and `rejection_reason` SHALL be `null`

#### Scenario: Rejected trade - data latency
- **WHEN** `dataLatency` exceeds 15 seconds
- **THEN** `is_approved` SHALL be `false` and `rejection_reason` SHALL reference the data freshness rule

### Requirement: Kill switch rule 1 - Data freshness
The evaluator SHALL reject trades when data latency exceeds 15 seconds.

#### Scenario: Stale data rejection
- **WHEN** `dataLatency` is 20 seconds
- **THEN** the trade SHALL be rejected with reason citing data staleness

### Requirement: Kill switch rule 2 - Liquidity check
The evaluator SHALL reject trades when bid-ask spread exceeds 15% of the bid price.

#### Scenario: Illiquid option rejection
- **WHEN** bid is $1.00 and ask is $1.20 (spread = 20% of bid)
- **THEN** the trade SHALL be rejected with reason citing liquidity

### Requirement: Kill switch rule 3 - Margin safety
The evaluator SHALL reject trades when projected margin utilization exceeds 60%.

#### Scenario: Margin breach rejection
- **WHEN** projected margin utilization is 65%
- **THEN** the trade SHALL be rejected with reason citing margin risk

### Requirement: Kill switch rule 4 - Early assignment
The evaluator SHALL reject ITM covered call trades when ex-dividend date is within 5 days.

#### Scenario: Dividend risk rejection
- **WHEN** selling an ITM covered call with 3 days to ex-dividend
- **THEN** the trade SHALL be rejected with reason citing early assignment risk

### Requirement: Kill switch rule 5 - Yield compliance
The evaluator SHALL reject trades when mid-price annualized yield falls outside the 7%-20% range.

#### Scenario: Low yield rejection
- **WHEN** annualized yield calculates to 4%
- **THEN** the trade SHALL be rejected with reason citing yield below minimum threshold

### Requirement: Annualized yield calculation
The evaluator SHALL compute annualized yield as `(midPrice / strike) × (365 / dte) × 100` where `midPrice = (bid + ask) / 2`.

#### Scenario: Correct calculation
- **WHEN** bid=5.0, ask=5.4, strike=450, dte=45
- **THEN** annualized yield SHALL be approximately `(5.2/450)×(365/45)×100 ≈ 9.37%`

### Requirement: Execution plan generation
For approved trades, the evaluator SHALL output a `recommended_order_type` of "Limit", a `limit_price` slightly above bid (bid + spread×0.3), and the calculated `annualized_yield_est`.

#### Scenario: Limit price calculation
- **WHEN** bid=5.0, ask=5.4
- **THEN** limit_price SHALL be approximately `5.0 + 0.4×0.3 = 5.12`
