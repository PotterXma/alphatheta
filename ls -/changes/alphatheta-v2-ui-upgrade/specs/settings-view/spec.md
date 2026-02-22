## ADDED Requirements

### Requirement: API key vault
The Settings view SHALL display a masked API key field (`****-ABCD`) with a visibility toggle button and a "读写模式 / Read-Write" permission badge.

#### Scenario: Toggle key visibility
- **WHEN** user clicks the visibility toggle
- **THEN** the API key SHALL alternate between masked (`****-ABCD`) and full display

### Requirement: System terminal
The Settings view SHALL include a console panel: black background (`#0a0a0a`), green monospace text (`#4ade80`), fixed height ~200px, vertical scroll, auto-scroll to bottom.

#### Scenario: Terminal renders logs
- **WHEN** Settings view loads with `systemLogs` entries
- **THEN** each log SHALL display on a separate line in green monospace text

#### Scenario: Auto-scroll
- **WHEN** logs exceed the visible area
- **THEN** the terminal SHALL auto-scroll to show the most recent entry

### Requirement: i18n labels
Settings view title and terminal title SHALL use `data-i18n` attributes.

#### Scenario: Labels switch
- **WHEN** language switches to `en`
- **THEN** "系统设置" SHALL become "Settings" and "系统健康终端" SHALL become "System Terminal"
