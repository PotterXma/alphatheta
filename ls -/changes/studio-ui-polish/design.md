## Architecture

纯前端 CSS/HTML 重构 — 无后端变更、无新依赖。三个文件协同修改：

```
index.html          →  DOM 骨架重写 (新 class 命名)
style.css           →  删除旧 Studio CSS, 写入新暗黑玻璃态样式
strategy_studio.js  →  renderLegs() 模板字符串适配新 class
```

## Layout Decision

### 两栏 Grid (左 6 : 右 4)

```
┌─────────────────────────────────────────────────────┐
│  .studio-toolbar  [模板 ▾]  [+ 添加腿]  [清空]       │
├────────────────────────────┬────────────────────────┤
│  .studio-left-panel        │ .studio-right-panel    │
│  ┌──────────────────────┐  │ ┌────────────────────┐ │
│  │ .legs-header         │  │ │ .chart-card        │ │
│  │ 动作 类型 到期 行权...│  │ │ #payoffChart 320px │ │
│  ├──────────────────────┤  │ └────────────────────┘ │
│  │ .leg-row  #1         │  │ ┌────────────────────┐ │
│  │ .leg-row  #2         │  │ │ .metrics-grid 2×2  │ │
│  │ .leg-row  #3         │  │ │ Net Premium (span2)│ │
│  │ .leg-row  #4         │  │ │ MaxP  MaxL  BE  EC │ │
│  └──────────────────────┘  │ └────────────────────┘ │
└────────────────────────────┴────────────────────────┘
```

**Grid 定义**: `grid-template-columns: 1fr 400px` — 左栏流式，右栏固定 400px 保证 ECharts 图表可读性。
**Breakpoint**: `@media (max-width: 1024px)` → 单栏堆叠。

## CSS 策略

### 1. 删除 → 重写 (非增量补丁)

旧 Studio CSS (~280 行) 全部删除，替换为新样式块。原因：
- 旧样式使用 `grid-template-columns: 32px 60px 90px...` 的 8 列硬编码 Grid — 在窄屏上崩坏
- 新方案改用 Flexbox `.leg-row` — 每个控件自然伸缩

### 2. CSS 变量集中管理

```css
:root {
  --studio-bg: rgba(15, 23, 42, 0.6);
  --studio-border: rgba(255, 255, 255, 0.08);
  --studio-accent: #06b6d4;
  --studio-glow: 0 0 10px rgba(6, 182, 212, 0.3);
  --studio-profit: #10b981;
  --studio-loss: #ef4444;
  --studio-text: #e2e8f0;
  --studio-muted: #64748b;
  --studio-input-bg: rgba(15, 23, 42, 0.8);
}
```

### 3. 控件重置优先级

Form Reset 要用 `#view-signal` 前缀限定作用域，避免污染其他 Tab:
```css
#view-signal select,
#view-signal input,
#view-signal button { ... }
```

## renderLegs() 适配

`strategy_studio.js` 中 `renderLegs()` 的 HTML 模板字符串需要更新 class 命名：

| 旧 class | 新 class | 变化 |
|----------|---------|------|
| `.leg-row` (Grid) | `.leg-row` (Flexbox) | 布局方式改变 |
| `.leg-toggle` | `.leg-action-toggle` | 语义更明确 |
| `.leg-type-group` | `.leg-type-group` | 不变 |
| `.leg-type-btn` | `.leg-type-btn` | 不变 |
| `.leg-input` | `.leg-input` | 不变 |
| `.leg-strike-wrapper` | `.leg-strike-wrapper` | 不变 |
| `.leg-delete` | `.leg-delete` | 不变 |

变化极小 — 主要是 `.leg-toggle` → `.leg-action-toggle` 以及外层 Grid 转 Flex。

## DOM ID 保障

所有功能性 ID 保持不变 — 仅修改 `class` 和 HTML 嵌套层级。JS 绑定零改动：
- `studioTemplateSelect`, `studioAddLeg`, `studioClearAll`
- `legsContainer`, `payoffChart`
- `studioNetPremium`, `studioNetLabel`
- `studioMaxProfit`, `studioMaxLoss`, `studioBreakeven`, `studioCollateral`

## 风险

| 风险 | 缓解 |
|------|------|
| 旧 CSS 删除后其他组件受影响 | 新样式全部用 `.studio-*` 前缀或 `#view-signal` 限定 |
| Mini Chain Panel 样式丢失 | 保留 `.mini-chain-panel` 系列 CSS 不删 |
| ECharts resize 异常 | `onShow()` 已有 `requestAnimationFrame(resize)` |
