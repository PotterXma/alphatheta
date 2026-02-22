## ADDED Requirements

### Requirement: Sidebar navigation panel
The system SHALL render a fixed-width (240px) glassmorphic sidebar on the left side with 5 navigation menu items, each with an SVG icon and i18n-driven label.

#### Scenario: Sidebar renders on load
- **WHEN** the page loads
- **THEN** a sidebar SHALL appear with menu items: Dashboard, Signal & Execute, Sandbox, Lifecycle & Reports, Settings

#### Scenario: Active route highlighting
- **WHEN** the user clicks a sidebar menu item
- **THEN** that item SHALL be highlighted with a cyan left border accent, and the corresponding view SHALL become visible

### Requirement: Hash-based SPA routing
The system SHALL use `window.location.hash` to drive view switching. Five view containers SHALL exist in the DOM, with only the active one visible.

#### Scenario: Route change via sidebar click
- **WHEN** the user clicks "策略沙盒" in the sidebar
- **THEN** `location.hash` SHALL change to `#sandbox` and only the sandbox view SHALL be visible

#### Scenario: Direct hash navigation
- **WHEN** the user navigates to `#settings` directly in the URL
- **THEN** the Settings view SHALL be displayed and the sidebar SHALL highlight the Settings item

#### Scenario: Default route
- **WHEN** the page loads with no hash or an invalid hash
- **THEN** the Dashboard view SHALL be displayed by default

### Requirement: Sidebar responsive collapse
The sidebar SHALL collapse to icon-only mode (64px width) on viewports narrower than 900px.

#### Scenario: Narrow viewport
- **WHEN** viewport width is less than 900px
- **THEN** sidebar SHALL show icons only and main content area SHALL adjust its left margin accordingly
