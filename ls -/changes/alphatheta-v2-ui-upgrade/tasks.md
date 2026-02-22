## 1. Foundation: CSS Design System & Global Layout

- [x] 1.1 Update `:root` CSS variables — add new tokens for sidebar width, terminal colors, kill-switch red, glow effects
- [x] 1.2 Create sidebar HTML structure with 5 nav items (SVG icons + `data-i18n` labels)
- [x] 1.3 Style sidebar: fixed 240px glassmorphic panel, active item cyan left-border, responsive collapse to 64px at <900px
- [x] 1.4 Create main content area (`margin-left: 240px`) with 5 view containers (`#view-dashboard`, `#view-signal`, `#view-sandbox`, `#view-lifecycle`, `#view-settings`)
- [x] 1.5 Style top header bar: full-width, flex layout for ticker + kill switch + lang toggle + status + clock

## 2. i18n System

- [x] 2.1 Define `I18N` dictionary object with `en` and `zh` keys covering all static labels (~30+ keys)
- [x] 2.2 Implement `APP_STATE` global state object (`lang`, `currentView`, `isHalted`)
- [x] 2.3 Implement `t(key)` function with key-as-fallback
- [x] 2.4 Implement `applyI18n()` — query all `[data-i18n]` elements and update `textContent`
- [x] 2.5 Implement `renderAll()` — calls `applyI18n()` + all view render functions
- [x] 2.6 Build language toggle pill button UI in header, wire click → toggle `APP_STATE.lang` → `renderAll()`

## 3. SPA Routing

- [x] 3.1 Implement `navigateTo(viewId)` — hide all views, show target, update sidebar active state, update `location.hash`
- [x] 3.2 Wire `hashchange` listener + sidebar click handlers
- [x] 3.3 Set default route to Dashboard on load (no hash or invalid hash)

## 4. News Ticker

- [x] 4.1 Create ticker bar HTML above header, full-width
- [x] 4.2 Add `@keyframes marquee` CSS animation (`translateX(0) → translateX(-50%)`)
- [x] 4.3 Implement `renderTicker()` — builds duplicated news list HTML from i18n-driven content, restarts animation on language switch

## 5. Kill Switch

- [x] 5.1 Create kill switch button HTML in header (red styling)
- [x] 5.2 Style: default red, halted state amber blinking animation
- [x] 5.3 Implement click handler: toggle `APP_STATE.isHalted`, toggle overlay, disable/enable execute buttons

## 6. Dashboard View (View A)

- [x] 6.1 Create portfolio net value display (large text, glassmorphic card)
- [x] 6.2 Create margin utilization progress bar with dynamic width + color threshold (green <60%, amber ≥60%)
- [x] 6.3 Create 3 radar cards: VIX (with IV Rank), SPY (price vs SMA200), QQQ (price vs SMA200)
- [x] 6.4 Implement `renderDashboard()` — populate all values from mock data, apply VIX color classes, trend arrows

## 7. Signal & Execution View (View B)

- [x] 7.1 Create dual-column grid layout: left (action panel) + right (rationale panel)
- [x] 7.2 Build action panel: badge, signal fields grid, execute button
- [x] 7.3 Build rationale panel: darker background, ordered list of reasons
- [x] 7.4 Style execute button with dynamic gradient (buy=emerald, sell=cyan) + glow
- [x] 7.5 Implement `renderSignal()` — populate from mock data, set button variant, check halt state
- [x] 7.6 Responsive: single-column fallback at <900px

## 8. Strategy Sandbox View (View C)

- [x] 8.1 Create parameter controls: strategy dropdown, ticker dropdown, DTE range slider (7-90), strike input, premium input
- [x] 8.2 Style slider with custom CSS (track + thumb)
- [x] 8.3 Create projection results panel: net cost, break-even, max profit, annualized yield (with glow)
- [x] 8.4 Implement `calculateProjections()` — compute all 4 metrics from current parameter values
- [x] 8.5 Wire `input` event listeners on all controls → trigger `calculateProjections()` on change

## 9. Lifecycle & Reports View (View D)

- [x] 9.1 Create positions table with columns: ticker, type, strike, DTE, P&L, actions
- [x] 9.2 Add DTE ≤14 amber row highlighting + blinking ⚠ icon
- [x] 9.3 Add "展期" roll button per row → `alert()` with simulated roll calculation
- [x] 9.4 Create card-flow alternative view for positions
- [x] 9.5 Add `@media (max-width: 768px)` to hide table, show card view
- [x] 9.6 Create performance report panel: 2 metric cards (automated ops + total premium)
- [x] 9.7 Implement Canvas mini trend chart (equity curve + 10% dashed baseline) with HiDPI scaling
- [x] 9.8 Implement `renderLifecycle()` — populate table + cards + report from mock data

## 10. Settings View (View E)

- [x] 10.1 Create API key vault UI: masked input (`****-ABCD`) + visibility toggle button (👁️) + "读写模式" badge
- [x] 10.2 Implement visibility toggle logic
- [x] 10.3 Create system terminal panel: black bg, green monospace text, 200px height, overflow-y auto
- [x] 10.4 Implement `renderTerminal()` — populate log lines, auto-scroll to bottom

## 11. Mock Data & Initialization

- [x] 11.1 Define complete `MOCK_DATA` object matching v7.0 JSON schema (portfolio, radar, sandbox, signal, positions, tracking, systemLogs, tickerNews)
- [x] 11.2 Implement `DOMContentLoaded` init: set default state, render all views, start clock, setup event listeners

## 12. Responsive & Polish

- [x] 12.1 Test and refine all responsive breakpoints (900px sidebar collapse, 768px card view, 600px single-column)
- [x] 12.2 Add micro-animations: card hover transitions, button press effects, sidebar hover expand
- [x] 12.3 Custom scrollbar styling for all scrollable areas
- [x] 12.4 Final cross-browser visual check
