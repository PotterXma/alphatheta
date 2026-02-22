## Context

`view-lifecycle` section in `index.html` (lines 398-454) currently has:
1. A positions table (`.positions-card`) with roll-modal support
2. A performance report card (`.report-card`) containing:
   - Two metric cards: 自动执行次数 + 累计权利金
   - An ECharts equity curve (`#equityCurveChart`)
   - A hidden equity summary (`#equitySummary`)

JS controller: `js/views/portfolio.js` — `renderPositions()`, `renderReport()`, `EquityCurveManager`

All data comes from `MOCK_DATA` in `js/store/index.js`. No backend changes needed.

## Goals / Non-Goals

**Goals:**
- Insert a `.portfolio-hud` grid **above** the positions table inside `view-lifecycle`
- Refactor `.report-metrics` area into a Bot Telemetry card with animated status beacon
- Add a `.perf-metrics-grid` **below** the equity curve chart
- Pure CSS dark glassmorphism, no new JS framework dependencies
- All new data sourced from expanded `MOCK_DATA` fields

**Non-Goals:**
- Backend API endpoints for real HUD / telemetry data (tracked separately)
- Mobile-first responsive breakpoints (will address in a future change)
- i18n keys for new labels (will add in a follow-up)

## Decisions

### 1. HUD Position: Inside `view-lifecycle`, before `.positions-card`

**Choice**: Insert as first child of `#view-lifecycle`, after the `<h1>` header.

**Rationale**: The HUD is account-level context that informs how the trader reads the positions below. Placing it at the top creates a natural top-down information flow: risk overview → positions → performance.

**Alternative considered**: Place in dashboard view — rejected because the dashboard already has `portfolio-row` cards and this would duplicate margin info.

### 2. Margin Progress Bar: Pure CSS with `data-*` attribute threshold

**Choice**: Use a `<div class="margin-bar-fill">` with inline `style="width: X%"`, and apply `.margin-danger` class via JS when `>= 80%`.

**Rationale**: CSS custom properties + class toggling = zero external deps. The threshold check lives in `renderHUD()` as a simple ternary.

**Alternative considered**: CSS `@container` query — too new, no Safari < 16 support.

### 3. Bot Telemetry Beacon: CSS `@keyframes` pulse animation

**Choice**: A `<span class="beacon beacon--scanning">` element with 3 state classes: `--scanning` (cyan pulse), `--halted` (red pulse), `--standby` (amber static). The animation uses `box-shadow` expansion.

**Rationale**: Pure CSS animation with no JS timer, state driven by class swap in `renderBotTelemetry()`.

### 4. Performance Metrics Grid: 4-column CSS Grid

**Choice**: `.perf-metrics-grid` using `grid-template-columns: repeat(4, 1fr)` with individual `.perf-metric-card` items.

**Rationale**: Consistent with existing `.metrics-grid` in strategy studio. Each card has `.metric-label` + `.metric-value` with conditional color classes.

### 5. Data Architecture: Extend `MOCK_DATA` with nested objects

```js
MOCK_DATA.hud = {
    marginUtilization: 68,    // percent
    netSpyDelta: -42.5,       // SPY-equivalent delta
    netTheta: 185.30,         // daily theta income $
};

MOCK_DATA.botTelemetry = {
    status: "scanning",       // "scanning" | "halted" | "standby"
    todayOrders: 3,
    apiLatencyMs: 45,
};

MOCK_DATA.perfMetrics = {
    winRate: 78.5,
    maxDrawdown: -12.4,
    profitFactor: 1.85,
    sharpeRatio: 1.42,
};
```

### 6. CSS Design Tokens

All new components use the existing design system:
- Glass background: `rgba(15, 23, 42, 0.6)` with `backdrop-filter: blur(16px)`
- Border: `1px solid rgba(0, 229, 255, 0.12)`
- Accent cyan: `#00e5ff`
- Success green: `#22c55e`
- Danger red: `#ef4444`
- Warning amber: `#f59e0b`
- Mono font: `'JetBrains Mono', monospace`

## File Change Map

| File | Action | Details |
|------|--------|---------|
| `index.html` | MODIFY | Insert HUD grid, refactor report-metrics, add perf-metrics-grid inside `view-lifecycle` |
| `style.css` | MODIFY | Add `.portfolio-hud`, `.bot-telemetry`, `.perf-metrics-grid`, beacon keyframes |
| `js/views/portfolio.js` | MODIFY | Add `renderHUD()`, `renderBotTelemetry()`, `renderPerfMetrics()`, call from `initPortfolioView()` |
| `js/store/index.js` | MODIFY | Extend `MOCK_DATA` with `hud`, `botTelemetry`, `perfMetrics` objects |

## Risks / Trade-offs

- **[Risk] Mock data may diverge from real API shape** → Mitigation: Keep mock structure intentionally simple so backend can easily match it later
- **[Risk] HUD adds visual weight to an already info-dense page** → Mitigation: Use compact single-row layout with subtle glass effect, not full card height
- **[Trade-off] No i18n support in v1** → Acceptable for now; English/CN labels hardcoded, will be extracted in follow-up
- **[Trade-off] Beacon animation on low-power mode** → CSS `prefers-reduced-motion` media query will disable pulse
