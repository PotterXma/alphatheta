## ADDED Requirements

### Requirement: Full-width ticker bar
The system SHALL render a narrow scrolling news bar above the main header, spanning full viewport width with dark semi-transparent background.

#### Scenario: Ticker visible on load
- **WHEN** the page loads
- **THEN** news headlines SHALL scroll right-to-left in a seamless CSS animation loop

### Requirement: i18n-driven content
Ticker content SHALL rebuild when language switches using the corresponding language's news array.

#### Scenario: Language switch rebuilds ticker
- **WHEN** user switches from `zh` to `en`
- **THEN** ticker SHALL display English headlines
