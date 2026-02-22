## ADDED Requirements

### Requirement: Active positions table
The Lifecycle view upper section SHALL display a glassmorphic table with ticker, type, strike, DTE, P&L columns. Rows with DTE ≤ 14 SHALL have amber highlight.

#### Scenario: DTE warning highlight
- **WHEN** a position has DTE=14
- **THEN** the row SHALL have amber background and a blinking ⚠ icon

### Requirement: 1-Click Roll button
Each position row SHALL have a "展期" action button that triggers a simulated roll calculation alert.

#### Scenario: Roll button click
- **WHEN** user clicks the roll button on a position
- **THEN** an alert SHALL display with suggested new expiry date and estimated premium

### Requirement: Responsive card view
At viewport width < 768px, the positions table SHALL be hidden and replaced with a card-flow layout.

#### Scenario: Mobile card view
- **WHEN** viewport is narrower than 768px
- **THEN** each position SHALL render as an individual glass card stacked vertically

### Requirement: Performance report panel
The lower section SHALL display two metric cards ("Automated Ops this Month" and "Total Premium Collected") plus a Canvas mini trend chart (equity curve + 10% annualized baseline).

#### Scenario: Report metrics render
- **WHEN** `tracking.automatedOps=18` and `tracking.totalPremiumCollected=4250`
- **THEN** "18" SHALL appear for ops count and "$4,250.00" for premium collected

#### Scenario: Equity trend chart
- **WHEN** the report panel renders
- **THEN** a Canvas chart SHALL display a simulated equity curve with a dashed 10% benchmark line
