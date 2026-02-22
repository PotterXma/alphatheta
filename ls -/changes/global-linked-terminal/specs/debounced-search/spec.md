## ADDED Requirements

### Requirement: Input field has 300ms debounce
The system SHALL debounce the watchlist search input by 300ms. No API call SHALL be made until 300ms have elapsed since the last keystroke.

#### Scenario: Rapid typing
- **WHEN** user types "A", "AP", "APL" in quick succession (under 300ms between keystrokes)
- **THEN** only one API call is made after 300ms of inactivity, with query "APL"

#### Scenario: Slow typing
- **WHEN** user types "A", waits 500ms, then types "P"
- **THEN** two API calls are made: one for "A" and one for "AP"

### Requirement: Dropdown displays matching tickers with company names
The system SHALL display a glassmorphism dropdown overlay below the input field showing matching tickers and their company names when search results are returned.

#### Scenario: Matching results found
- **WHEN** debounced query "AAP" returns results [AAPL - Apple Inc.]
- **THEN** a dropdown with backdrop-filter blur appears showing "AAPL — Apple Inc."

#### Scenario: No results
- **WHEN** debounced query "XYZZ" returns zero results
- **THEN** dropdown shows "未找到匹配标的"

#### Scenario: Click to add
- **WHEN** user clicks "AAPL" in the dropdown
- **THEN** system calls POST /settings/watchlist with ticker "AAPL", closes dropdown, and refreshes table

### Requirement: Dropdown closes on outside click or Escape
The system SHALL close the dropdown when the user clicks outside of it or presses the Escape key.

#### Scenario: Click outside
- **WHEN** dropdown is open and user clicks elsewhere on the page
- **THEN** dropdown closes

#### Scenario: Escape key
- **WHEN** dropdown is open and user presses Escape
- **THEN** dropdown closes
