## ADDED Requirements

### Requirement: Pre-Trade Buying Power Validation
Margin must be calculated and funds locked BEFORE order submission.

#### Scenario: Naked put margin (Reg T)
- **WHEN** a user submits a Sell Put order
- **THEN** margin requirement = max(20% × underlying_price × 100 + premium × 100 - OTM_amount × 100, 10% × strike × 100 + premium × 100), and this amount is pre-deducted from `users.cash_balance` using `SELECT ... FOR UPDATE`

#### Scenario: Covered call margin
- **WHEN** a user submits a Sell Call order AND owns ≥ 100 shares of the underlying per contract
- **THEN** margin requirement = 0 (fully covered), but the underlying shares are flagged as encumbered

#### Scenario: Cash-secured put margin
- **WHEN** a user submits a Sell Put with sufficient cash to buy 100 shares at strike
- **THEN** margin requirement = strike × 100 × quantity (full cash collateral)

#### Scenario: Spread margin (defined risk)
- **WHEN** a user submits a vertical spread (e.g., Bull Put Spread)
- **THEN** margin requirement = (wide_strike - narrow_strike) × 100 × quantity - net_premium_received

#### Scenario: Insufficient buying power
- **WHEN** the calculated margin exceeds `users.cash_balance - users.margin_used`
- **THEN** the order is REJECTED with error "Insufficient buying power: available $X, required $Y"

---

### Requirement: Pessimistic Fund Locking

#### Scenario: Concurrent order submission
- **WHEN** two orders for the same user are submitted simultaneously
- **THEN** the second order MUST wait for the first to release its row lock on `users`, preventing double-spend

#### Scenario: Order cancellation refund
- **WHEN** a pending order is canceled before fill
- **THEN** the pre-deducted margin is returned to `users.cash_balance` atomically
