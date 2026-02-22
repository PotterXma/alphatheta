## ADDED Requirements

### Requirement: Kill switch button
The system SHALL render a red "紧急暂停 / Halt Trading" button in the top header bar.

#### Scenario: Activate halt
- **WHEN** the user clicks the kill switch while `isHalted` is `false`
- **THEN** `APP_STATE.isHalted` SHALL become `true`, the button SHALL change to amber blinking state, all execute buttons SHALL be disabled, and a semi-transparent overlay message SHALL appear

#### Scenario: Deactivate halt
- **WHEN** the user clicks the kill switch while `isHalted` is `true`
- **THEN** `APP_STATE.isHalted` SHALL become `false`, the button SHALL return to red, execute buttons SHALL re-enable, and the overlay SHALL disappear

### Requirement: i18n label
The kill switch button text SHALL use `data-i18n="kill_switch"`.

#### Scenario: Label in English
- **WHEN** language is `en`
- **THEN** button SHALL display "Halt Trading"
