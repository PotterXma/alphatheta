## ADDED Requirements

### Requirement: Portfolio net value display
The system SHALL display the total account net value prominently in the Dashboard view.

#### Scenario: Net value renders
- **WHEN** Dashboard view is active
- **THEN** "$125,430.50" SHALL be displayed as the total net value

### Requirement: Margin utilization progress bar
The system SHALL display a progress bar showing current margin usage percentage. Bar color SHALL be emerald green below 60% and amber at or above 60%.

#### Scenario: Normal margin level
- **WHEN** `marginUsed` is "45%"
- **THEN** the progress bar SHALL fill to 45% with emerald green color

#### Scenario: Warning margin level
- **WHEN** `marginUsed` exceeds 60%
- **THEN** the progress bar SHALL change to amber color

### Requirement: Macro radar cards
The Dashboard SHALL display three glassmorphic cards for VIX (with IV Rank), SPY (price vs SMA200), and QQQ (price vs SMA200).

#### Scenario: VIX card with IV Rank
- **WHEN** VIX is 18.5 and QQQ IV Rank is 65
- **THEN** the VIX card SHALL display "18.5" and include "IV Rank: 65%" for QQQ

### Requirement: i18n labels
All Dashboard labels SHALL use `data-i18n` attributes.

#### Scenario: Labels switch to English
- **WHEN** language is `en`
- **THEN** "保证金使用率" SHALL become "Margin Utilization"
