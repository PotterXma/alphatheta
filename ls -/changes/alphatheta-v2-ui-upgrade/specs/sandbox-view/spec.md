## ADDED Requirements

### Requirement: Parameter controls
The Sandbox view SHALL provide: strategy type dropdown, underlying ticker dropdown, DTE range slider (7-90, default 45), strike price input, premium input.

#### Scenario: DTE slider interaction
- **WHEN** user drags DTE slider to 30
- **THEN** displayed DTE SHALL update and all projections SHALL recompute

### Requirement: Real-time projection calculations
The system SHALL compute: Net Cost (strike×100 − premium×100), Break-even (strike − premium), Max Profit (premium×100), Annualized Yield ((premium/strike) × (365/DTE) × 100).

#### Scenario: Default values calculation
- **WHEN** strike=450, premium=5.20, DTE=45
- **THEN** Net Cost="$44,480.00", Break-even="$444.80", Max Profit="$520.00", Annualized Yield≈"9.37%"

### Requirement: Annualized yield glow highlight
The Annualized Yield value SHALL have a visible glow/text-shadow effect.

#### Scenario: Visual emphasis
- **WHEN** sandbox renders
- **THEN** annualized yield SHALL have a distinct glow differentiating it from other metrics
