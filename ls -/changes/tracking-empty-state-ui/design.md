## Context

跟踪页面 (`#view-lifecycle`) HTML 结构:
- **HUD**: 3 单元格 — Margin Utilization (进度条 + 百分比), Net SPY Delta, Net Theta/Day
- **持仓表**: 9 列 (交易标的/类型/行权价/到期日/剩余天数/初始权利金/当前价值/盈亏比例/操作), `<tbody id="positionsBody">` 动态填充
- **绩效报告**: 遥测状态 (beacon + 指标) + Equity Curve 图表 (ECharts, 360px) + 4 格绩效指标 (Win Rate / Max Drawdown / Profit Factor / Sharpe)
- **Equity 摘要**: 总收益 / 最大回撤 / Sharpe (默认 hidden)

$100k 空仓期 = 全部面板需要优雅的零状态而非 NaN/空白。

## Decisions

### D1: 空状态设计 — 雷达扫描动效

**选择**: SVG 圆形雷达扫描动画 (纯 CSS `@keyframes rotate`)

不用 Lottie (过重)。一个 SVG 圆圈 + 旋转扫描线 + `conic-gradient` 实现科技感雷达，耗时 < 1KB。配合幽蓝色辉光 (`#06b6d4` 青色)。

### D2: 操作按钮设计 — 暗黑玻璃态微型按钮

**选择**: `.action-btn` 基础样式 + 子类 `.close-btn` (hover 红色微光) / `.roll-btn` (hover 青色微光)

`backdrop-filter: blur(8px)` + `border: 1px solid rgba(255,255,255,0.08)` + 各自 hover `box-shadow` 颜色。按钮高 28px, 字号 12px, 与表格行高匹配。

### D3: 盈亏双维格式

**选择**: `formatPnL(abs, pct)` → `+$420.00 (+85.7%)` / `-$120.00 (-24.5%)`

正值绿色 (`#10b981`), 负值红色 (`#f43f5e`), 零值灰色。双维并排在同一 `<td>` 中。

### D4: N/A 指标处理

**选择**: 无交易历史时统一显示 `N/A` 而非 `0%` 或 NaN

`hasTradeHistory` 布尔标记。`N/A` 用 `color: #475569` 暗灰色淡化。

### D5: Equity Curve 初始锚点

**选择**: `series: [[today, 100000]]` + `markLine` 水平虚线 at $100k

单点不画折线 (无法画)，但 markLine 在 y=100000 处画一条虚线 + 标签 "初始资金 $100K"。图表启用但无数据。

### D6: 方向数量格式

**选择**: `买入 (Long) · 1张` 绿/青色 vs `卖出 (Short) · 2张` 红色

用 `.direction-long` (绿) / `.direction-short` (红) CSS 类。数量用 `·` 分隔符。
