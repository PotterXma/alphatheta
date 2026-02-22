## Context

Strategy Studio (`#view-signal`) has a 2-column layout (`.studio-container`):
- **Left**: `.studio-left-panel` — option legs table
- **Right**: `.studio-right-panel` — payoff chart, metrics grid, greeks grid

Three components suffer from visual regressions:
1. `.recommendation-panel` — already at correct DOM position (above `.studio-container`), but missing full-width styles and horizontal flex alignment
2. `.sim-controls` — positioned inside `.chart-card` correctly, but overlaps `.chart-card-title` due to missing separator
3. `.greeks-grid` — already uses `repeat(4, 1fr)` but cards are too tall and labels too large

## Goals / Non-Goals

**Goals:**
- Fix recommendation panel to fill full viewport width with proper spacing
- Add visual separator between sim controls and chart title
- Tighten greeks grid card proportions (smaller padding, smaller label, bigger value)
- Restyle `<input type="range">` with cyan track fill for active portion
- All changes CSS-only where possible; minimal DOM tweaks

**Non-Goals:**
- Changing any JS business logic or data flow
- Adding new features or data fields
- Responsive breakpoints below 1024px (existing media query handles mobile)

## Decisions

### 1. Recommendation Panel — CSS-only fix
**Current state**: DOM position is correct (line 195, above `.studio-container` at line 203). CSS `.recommendation-panel` (L3121) only has `margin-bottom: 16px`.
**Fix**: Add `margin-bottom: 20px` and ensure `.rec-cards` 3-column grid has proper gap. No DOM change needed.
**Why**: The original user report described DOM reordering, but inspection shows it's already in the right spot. The visual issue comes from insufficient margin.

### 2. Sim Controls — Add `.chart-controls` wrapper
**Current state**: `.sim-controls` (L3560) sits directly under `.chart-card-title` with only `margin-bottom: 8px` separating content.
**Fix**: Wrap sim controls in a `.chart-controls` div with `background: rgba(0,0,0,0.2)`, `border-bottom: 1px solid rgba(255,255,255,0.05)`, and `padding: 15px`. This creates a visually distinct control panel.
**DOM change**: Add `<div class="chart-controls">` wrapper around `.sim-controls` in `index.html`.
**Why**: Clear visual boundary separates "controls" from "chart content".

### 3. Greeks Grid — Proportion tuning only
**Current state**: `.greeks-grid` (L3629) already uses `grid-template-columns: repeat(4, 1fr)` correctly.
**Fix**: Tighten `.greek-card` padding from `10px 8px` → `8px 6px`, reduce `.greek-symbol` font from `20px` → `16px`, enlarge `.greek-value` from `14px` → `16px`. More data density, less decorative overhead.
**Why**: The 4-column grid is correct, just proportionally wasteful.

### 4. Range Slider — Active track fill
**Current state**: `.sim-slider` (L3584) has static gray track.
**Fix**: Add CSS gradient trick using `linear-gradient` on the track background to show a cyan fill from left to the thumb position. JS already updates the slider; we add a CSS custom property `--val` set by the existing `oninput` handler.
**Fallback**: If the `--val` approach needs JS touch-up, add one line to existing slider event handlers — acceptable since it's presentation-only.

## Risks / Trade-offs

- **[Risk] DOM restructure breaks `getElementById` references** → Mitigated: only adding a wrapper div, not moving elements with IDs
- **[Risk] Slider active-track CSS varies across browsers** → Mitigated: using `-webkit-slider-runnable-track` + `::-moz-range-track` separate rules
- **[Trade-off] Minimal DOM change means recommendation panel spacing is CSS-only** → Acceptable: avoids any risk of breaking JS recommendation rendering
