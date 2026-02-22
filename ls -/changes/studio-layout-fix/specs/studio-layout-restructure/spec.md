## ADDED Requirements

### Requirement: Recommendation Panel Full-Width Isolation
The `.recommendation-panel` must render as a full-width block above the `.studio-container` two-column grid, with at least `20px` bottom margin separating it from the content below.

#### Scenario: Panel renders above studio columns
- **WHEN** the Strategy Studio view is visible
- **THEN** `.recommendation-panel` spans the full content width, `.rec-cards` displays as a 3-column grid, and no overlap exists with `.studio-left-panel` or `.studio-right-panel`

---

### Requirement: Chart Controls Container
A `.chart-controls` wrapper div must exist inside `.chart-card`, positioned between `.chart-card-title` and the ECharts `#payoffChart` div. It contains the T+n and IV slider groups.

#### Scenario: Sim controls visually separated from chart
- **WHEN** the payoff chart card renders
- **THEN** `.chart-controls` has a dark background (`rgba(0,0,0,0.2)`), bottom border (`1px solid rgba(255,255,255,0.05)`), and `15px` padding
- **THEN** slider labels, range inputs, and value displays are horizontally arranged within

#### Scenario: Range slider styled with cyan track
- **WHEN** user interacts with T+n or IV slider
- **THEN** the slider thumb is cyan (`#06b6d4`) with glow shadow
- **THEN** the active portion of the track (left of thumb) shows cyan fill

---

### Requirement: Greeks Grid Compact Layout
The `.greeks-grid` must display its 4 cards (Δ, Γ, Θ, V) in a single horizontal row using `grid-template-columns: repeat(4, 1fr)` with tightened proportions.

#### Scenario: Greek cards show data-dense layout
- **WHEN** the greeks grid renders
- **THEN** `.greek-card` padding is ≤ `10px 8px`
- **THEN** `.greek-value` font size ≥ `14px` with monospace font and bold weight
- **THEN** `.greek-label` font size ≤ `9px`, uppercase

#### Scenario: Positive/negative coloring
- **WHEN** a greek value is positive
- **THEN** it applies `.positive` class (green)
- **WHEN** a greek value is negative
- **THEN** it applies `.negative` class (red)

---

### Requirement: Zero JS Logic Changes
No JavaScript business logic, data flow, or event handler behavior may be altered. All element IDs must remain unchanged.

#### Scenario: Existing JS references intact
- **WHEN** the page initializes
- **THEN** all `getElementById` calls (`simDteSlider`, `simIvSlider`, `payoffChart`, `greekDelta`, `greekGamma`, `greekTheta`, `greekVega`, etc.) resolve to valid DOM elements
- **THEN** no console errors from missing element references
