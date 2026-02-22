## 1. Mock Data Extension

- [x] 1.1 Add `MOCK_DATA.hud` object (`marginUtilization`, `netSpyDelta`, `netTheta`) to `js/store/index.js`
- [x] 1.2 Add `MOCK_DATA.botTelemetry` object (`status`, `todayOrders`, `apiLatencyMs`) to `js/store/index.js`
- [x] 1.3 Add `MOCK_DATA.perfMetrics` object (`winRate`, `maxDrawdown`, `profitFactor`, `sharpeRatio`) to `js/store/index.js`

## 2. HTML Structure — Portfolio HUD

- [x] 2.1 Insert `.portfolio-hud` grid inside `#view-lifecycle` after `.view-header`, before `.positions-card`
- [x] 2.2 Add margin utilization cell with `.margin-bar-fill` progress element and percentage label
- [x] 2.3 Add Net SPY Delta cell with value element (`#hudNetDelta`)
- [x] 2.4 Add Net Theta cell with value element (`#hudNetTheta`)

## 3. HTML Structure — Bot Telemetry

- [x] 3.1 Replace `.report-metrics` div inside `.report-card` with `.bot-telemetry` container
- [x] 3.2 Add beacon element (`<span class="beacon">`) with status label
- [x] 3.3 Add today's orders count indicator (`#telemetryOrders`)
- [x] 3.4 Add API latency indicator (`#telemetryLatency`)

## 4. HTML Structure — Performance Metrics Grid

- [x] 4.1 Insert `.perf-metrics-grid` below `#equityCurveChart` wrapper, inside `.report-card`
- [x] 4.2 Add 4 metric cards: Win Rate, Max Drawdown, Profit Factor, Sharpe Ratio

## 5. CSS — Portfolio HUD

- [x] 5.1 Style `.portfolio-hud` as 3-column glassmorphism grid
- [x] 5.2 Style `.hud-margin-bar` and `.hud-margin-fill` with cyan fill + `.margin-danger` red variant
- [x] 5.3 Style Net Delta value with conditional `.text-success` / `.text-danger` coloring
- [x] 5.4 Style Net Theta value with cyan accent

## 6. CSS — Bot Telemetry

- [x] 6.1 Style `.bot-telemetry` card layout (beacon left, metrics right)
- [x] 6.2 Create `@keyframes beacon-pulse` animation for scanning/halted states
- [x] 6.3 Style `.beacon--scanning` (cyan), `.beacon--halted` (red), `.beacon--standby` (amber)
- [x] 6.4 Add `prefers-reduced-motion` media query to disable beacon animation

## 7. CSS — Performance Metrics Grid

- [x] 7.1 Style `.perf-metrics-grid` as 4-column grid with glassmorphic cells
- [x] 7.2 Style `.perf-metric-card` with label/value layout and conditional color classes

## 8. JavaScript — Render Functions

- [x] 8.1 Implement `renderHUD()` in `portfolio.js` — read `MOCK_DATA.hud`, populate DOM, apply margin danger class at ≥80%
- [x] 8.2 Implement `renderBotTelemetry()` — read `MOCK_DATA.botTelemetry`, set beacon class, populate order/latency values
- [x] 8.3 Implement `renderPerfMetrics()` — read `MOCK_DATA.perfMetrics`, populate values with conditional coloring
- [x] 8.4 Call all three render functions from `initPortfolioView()`

## 9. Verification

- [ ] 9.1 Visual check: HUD renders above positions table with correct layout
- [ ] 9.2 Visual check: Margin bar turns red when mock value set to ≥80%
- [ ] 9.3 Visual check: Beacon pulses with correct color per status
- [ ] 9.4 Visual check: Performance metrics grid renders below equity curve
- [ ] 9.5 Verify no console errors and existing functionality unbroken
