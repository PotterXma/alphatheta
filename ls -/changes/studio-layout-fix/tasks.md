## 1. CSS — Recommendation Panel Spacing

- [x] 1.1 Update `.recommendation-panel` to `margin-bottom: 20px`
- [x] 1.2 Verify `.rec-cards` grid (`repeat(3, 1fr)`) renders full-width above `.studio-container`

## 2. HTML — Chart Controls Wrapper

- [x] 2.1 Wrap `.sim-controls` inside a new `<div class="chart-controls">` in `.chart-card`, between `.chart-card-title` and `#payoffChart`

## 3. CSS — Chart Controls Styling

- [x] 3.1 Style `.chart-controls` with dark background, bottom border separator, and `15px` padding
- [x] 3.2 Add active-track cyan fill on `.sim-slider` using `linear-gradient` background
- [x] 3.3 Add `::-moz-range-progress` and `::-webkit-slider-runnable-track` rules for cross-browser track fill

## 4. CSS — Greeks Grid Proportion Tuning

- [x] 4.1 Tighten `.greek-card` padding to `8px 6px`
- [x] 4.2 Reduce `.greek-symbol` font-size to `16px`
- [x] 4.3 Increase `.greek-value` font-size to `16px`
- [x] 4.4 Reduce `.greek-label` font-size to `8px`

## 5. Verification

- [x] 5.1 Visual check: recommendation panel renders full-width with 20px gap below
- [x] 5.2 Visual check: sim controls have clear dark separator from chart title
- [x] 5.3 Visual check: greeks grid is compact 4-column row with prominent values
- [x] 5.4 Verify no console errors — all existing `getElementById` calls resolve
