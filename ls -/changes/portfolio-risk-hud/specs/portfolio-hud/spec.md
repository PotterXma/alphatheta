## ADDED Requirements

### Requirement: Margin utilization progress bar
The system SHALL display a horizontal progress bar showing current margin utilization as a percentage (0-100%). The bar fill color SHALL be cyan (`#00e5ff`) when utilization is below 80%, and SHALL switch to danger red (`#ef4444`) when utilization is at or above 80%. The percentage value SHALL be displayed in monospace font beside the bar.

#### Scenario: Normal margin utilization
- **WHEN** margin utilization is 68%
- **THEN** the progress bar fills to 68% width with cyan color, and the label reads "68%"

#### Scenario: Danger margin utilization
- **WHEN** margin utilization is 85%
- **THEN** the progress bar fills to 85% width with red color, and the `.margin-danger` class is applied

### Requirement: Net SPY Delta display
The system SHALL display the Net SPY Delta (portfolio-equivalent SPY delta exposure) as a prominent numeric value in the HUD grid. Positive values SHALL be styled green (`#22c55e`), negative values SHALL be styled red (`#ef4444`). The value SHALL use monospace font.

#### Scenario: Negative delta exposure
- **WHEN** Net SPY Delta is -42.5
- **THEN** the display shows "-42.5" in red text

#### Scenario: Positive delta exposure
- **WHEN** Net SPY Delta is 15.0
- **THEN** the display shows "+15.0" in green text

### Requirement: Net Theta daily income display
The system SHALL display the Net Theta value representing estimated daily time-decay income in USD. The value SHALL always be styled in cyan to emphasize its role as the primary income driver for option sellers.

#### Scenario: Theta income display
- **WHEN** Net Theta is $185.30
- **THEN** the display shows "$185.30" in cyan with label "Net Theta / Day"

### Requirement: HUD layout and positioning
The `.portfolio-hud` container SHALL be positioned as the first content element inside `#view-lifecycle`, immediately after the view header and before the positions table. It SHALL use a 3-column grid layout with glassmorphism styling consistent with the existing design system.

#### Scenario: HUD renders above positions
- **WHEN** the lifecycle view is displayed
- **THEN** the HUD grid appears above the `.positions-card` with 3 evenly-spaced metric cells
