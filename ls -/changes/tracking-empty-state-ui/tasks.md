## 1. CSS 基础样式

- [x] 1.1 添加 `.action-btn` 基础样式 (暗黑玻璃态, 28px 高, backdrop-filter)
- [x] 1.2 添加 `.close-btn` hover 红色微光 + `.roll-btn` hover 青色微光
- [x] 1.3 添加 `.direction-long` (绿色) / `.direction-short` (红色) 方向颜色类
- [x] 1.4 添加 `.pnl-positive` / `.pnl-negative` / `.pnl-zero` 盈亏颜色类
- [x] 1.5 添加 `.positions-empty-state` 居中容器 + 雷达 SVG 动效 CSS

## 2. 持仓表模板 (JS)

- [x] 2.1 实现 `renderPositionRow(position)` — 9 列 TR 模板 (含方向数量 + 双维盈亏 + 操作按钮)
- [x] 2.2 实现 `renderEmptyPositions()` — 雷达占位 colspan=9 + 提示文案
- [x] 2.3 在 `renderPositions(list)` 中: list.length === 0 → 调用空状态, 否则渲染数据行

## 3. HUD + 指标初始化

- [x] 3.1 实现 `initHUDDefaults()` — Margin 0%, Delta 0, Theta $0.00
- [x] 3.2 实现 `initPerfMetrics()` — Win Rate/Drawdown/PF/Sharpe 统一 N/A
- [x] 3.3 实现 `initTelemetry()` — beacon 绿色, 0 指令, $0.00 权利金

## 4. Equity Curve 图表

- [x] 4.1 ECharts 初始化: series [[today, 100000]] + markLine y=100000 虚线
- [x] 4.2 Equity 摘要区块: 显示并填充 $0.00 / 0% / N/A

## 5. 集成与验证

- [x] 5.1 在页面初始化函数中调用所有 init 函数
- [x] 5.2 重新 build + deploy web
- [ ] 5.3 浏览器验证: 空仓页面无 NaN, 雷达动效正常, HUD 归零
