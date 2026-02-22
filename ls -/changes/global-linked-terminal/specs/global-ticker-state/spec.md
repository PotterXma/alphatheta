## ADDED Requirements

### Requirement: Global active ticker state persists across page navigation
The system SHALL maintain a `globalActiveTicker` state that persists across SPA page navigation and survives page refresh via sessionStorage.

#### Scenario: Set ticker from Signal page
- **WHEN** user clicks a Top 3 recommended ticker "AMD" on the Signal page
- **THEN** `globalActiveTicker` is set to "AMD" and a `ticker-changed` event is dispatched

#### Scenario: Navigate to Sandbox after setting ticker
- **WHEN** `globalActiveTicker` is "AMD" and user navigates to Sandbox page
- **THEN** Sandbox page reads "AMD" and renders AMD-specific data

#### Scenario: Navigate to Lifecycle after setting ticker
- **WHEN** `globalActiveTicker` is "AMD" and user navigates to Lifecycle page
- **THEN** Lifecycle page reads "AMD" and renders AMD-specific data

### Requirement: Global ticker survives page refresh
The system SHALL persist `globalActiveTicker` in sessionStorage.

#### Scenario: Refresh browser
- **WHEN** `globalActiveTicker` is "NVDA" and user refreshes the page
- **THEN** on page load, `globalActiveTicker` is restored to "NVDA" from sessionStorage

### Requirement: Default ticker when none selected
The system SHALL default to "SPY" when no global ticker has been selected.

#### Scenario: First visit
- **WHEN** user opens the app for the first time with no sessionStorage
- **THEN** `globalActiveTicker` defaults to "SPY"
