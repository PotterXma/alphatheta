## ADDED Requirements

### Requirement: Risk approval badge
The signal view SHALL display a prominent badge showing CRO approval status: green "✓ 风控通过" for approved, red "✗ 风控否决" for rejected.

#### Scenario: Approved badge
- **WHEN** the CRO evaluator returns `is_approved: true`
- **THEN** a green approval badge SHALL appear in the signal view

#### Scenario: Rejected badge with reason
- **WHEN** the CRO evaluator returns `is_approved: false`
- **THEN** a red rejection badge SHALL appear with the `rejection_reason` displayed below

### Requirement: Execution plan panel
For approved trades, a panel SHALL display the recommended order type, limit price, and annualized yield estimate.

#### Scenario: Execution plan renders
- **WHEN** trade is approved with limit_price=5.12 and annualized_yield=9.37%
- **THEN** the panel SHALL show "Limit @ $5.12" and "年化 9.37%"

### Requirement: Scenario playbook cards
For approved trades, two side-by-side glassmorphic cards SHALL display the bullish surge and bearish crash playbooks.

#### Scenario: Playbook cards render
- **WHEN** trade is approved
- **THEN** two cards SHALL appear: one with bullish surge header (green accent) and one with bearish crash header (red accent)

### Requirement: Execute button gating
The execute button SHALL be disabled when CRO evaluation rejects the trade.

#### Scenario: Rejected trade disables button
- **WHEN** `is_approved` is `false`
- **THEN** the execute button SHALL be disabled and greyed out

### Requirement: i18n coverage
All new CRO UI labels SHALL use `data-i18n` attributes and support EN/ZH toggle.

#### Scenario: Labels switch
- **WHEN** language switches to `en`
- **THEN** "风控通过" SHALL become "Risk Approved" and "风控否决" SHALL become "Risk Rejected"
