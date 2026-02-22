## Why

AlphaTheta v2 的全程跟踪页面存在两个问题:
1. 活跃持仓表格中残留未完成的 `roll_btn` 占位符、缺少方向/数量列、盈亏格式不统一
2. 系统处于 $100,000 初始空仓期，所有表格和图表需要优雅的"零数据"状态，而非 NaN/空白

## What Changes

- **修复** 活跃持仓表 `<tr>` 模板 — 补齐操作按钮 (平仓/展期)、方向数量、盈亏双维展示
- **新增** 零数据空状态 UI — 科技感占位动效 + 提示文案
- **修复** HUD 面板归零 — Margin/Delta/Theta 初始化为 0/$0
- **修复** 运营报告指标 — Win Rate 等统计显示 N/A 而非 NaN
- **修复** Equity Curve 图表 — 起始锚点 [Today, $100k] + 水平基准虚线

## Capabilities

### New Capabilities
- `positions-empty-state`: 活跃持仓零数据状态 (科技感占位 + 扫描引擎状态)
- `positions-row-template`: 活跃持仓单行数据模板 (按钮修复 + 双维盈亏)
- `hud-metrics-init`: HUD/运营指标/图表的 $100k 空仓初始化

### Modified Capabilities
_(无)_

## Impact

- **`index.html`** — 持仓表结构修复
- **`style.css`** — 操作按钮样式 + 空状态居中 + 动效
- **`js/views/tracking.js`** 或相关视图 — 空状态渲染逻辑 + HUD 初始化 + 图表锚点
