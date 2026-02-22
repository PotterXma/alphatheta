## Overview

Strategy Studio 暗黑玻璃态视觉重构 — 将原始 UI 控件升级为华尔街量化终端美学标准。

## Requirements

### R1: CSS Grid 两栏布局

- 容器 `.studio-container` 使用 `display: grid; grid-template-columns: 1fr 400px;`
- 左栏 `.studio-left-panel` (构建区): 工具栏 + 腿列表
- 右栏 `.studio-right-panel` (推演区): 盈亏图表 + 资金 Metric 网格
- 响应式: `@media (max-width: 1024px)` 降级为单栏

### R2: 暗黑玻璃态设计规范

- 卡片背景: `rgba(15, 23, 42, 0.6)` + `backdrop-filter: blur(12px)`
- 微光边框: `border: 1px solid rgba(255, 255, 255, 0.08)`
- 卡片圆角: `border-radius: 12px`
- 悬浮阴影: `box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3)`

### R3: 色彩规范

| Token | 值 | 用途 |
|-------|----|------|
| 主题强调色 | `#06b6d4` | 按钮高亮、焦点边框 |
| 发光效果 | `box-shadow: 0 0 10px rgba(6,182,212,0.3)` | 主按钮 glow |
| 盈利绿 | `#10b981` | Credit、BUY |
| 亏损红 | `#ef4444` | Debit、SELL |
| 文字主色 | `#e2e8f0` | 正文 |
| 文字副色 | `#64748b` | 标签 |
| 背景深色 | `#0f172a` | 输入框 |

### R4: 控件重置

- `<select>`: 自定义 SVG 下拉箭头, 暗色背景, 聚焦时青色边框
- `<button>`: 主按钮=青色发光, 幽灵按钮=透明+白边
- `<input[type=number]>`: 隐藏 spin, 暗色, 聚焦青色
- `<input[type=date]>`: 统一暗色, picker 反色

### R5: 工具栏 `.studio-toolbar`

- Flexbox, `gap: 12px`
- 模板 `<select>` 最小宽度 260px
- `[+ 添加期权腿]`: 青色 + glow + `:hover` 放大
- `[清空]`: 透明 + 红色文字 + 红色边框

### R6: 腿卡片 `.leg-row`

- Flexbox 横向长条
- 背景 `rgba(15, 23, 42, 0.4)` + 微光边框
- `:hover` 提亮到 `rgba(30, 41, 59, 0.6)`
- Buy/Sell Toggle 胶囊形, Call/Put/Stock 3按钮组

### R7: 图表卡片 `.chart-card`

- 青色发光边框: `border: 1px solid rgba(6, 182, 212, 0.15)`
- `#payoffChart` 高度 320px

### R8: Metric 网格 `.metrics-grid`

- `grid-template-columns: 1fr 1fr; gap: 12px`
- Net Premium: `grid-column: span 2`, 字号 28px
- 其他 Metric: 字号 18px

### R9: DOM ID 保持不变

`studioTemplateSelect`, `studioAddLeg`, `studioClearAll`, `legsContainer`, `payoffChart`, `studioNetPremium`, `studioNetLabel`, `studioMaxProfit`, `studioMaxLoss`, `studioBreakeven`, `studioCollateral`
