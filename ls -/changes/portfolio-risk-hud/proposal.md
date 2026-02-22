## Why

AlphaTheta v2 的「全程跟踪与报告」(lifecycle view) 页面目前仅展示一张基础资金折线图和两个粗放的统计指标（本月自动执行次数、累计权利金）。作为一个期权卖方策略引擎，缺少保证金水位监控、全账户 Greeks 敞口、策略质量归因（胜率/回撤/盈亏比/Sharpe）以及自动化机器人的实时遥测状态。交易员无法在一个屏幕内掌控全局风险。

## What Changes

- **新增账户级风控头显 (Portfolio HUD)**: 在持仓表上方插入横向玻璃态网格，实时展示保证金利用率（进度条+阈值变色）、Net SPY Delta 等效敞口、Net Theta 日均时间收入
- **重构自动化运营卡片 → Bot Telemetry Card**: 将现有 report-metrics 区块改造为带呼吸灯动画的机器人遥测面板，新增状态指示、今日执行指令数、API 延迟指标
- **新增业绩归因指标网格 (Performance Metrics Grid)**: 在资金折线图下方新增一行紧凑的量化指标卡片，展示 Win Rate、Max Drawdown、Profit Factor、Sharpe Ratio
- **全局设计升级**: 数字统一使用 JetBrains Mono 等宽字体，玻璃态容器升级为双层边框 + 内发光效果

## Capabilities

### New Capabilities
- `portfolio-hud`: 账户级风控头显模块 — 保证金进度条、Net SPY Delta、Net Theta 三列 HUD 网格
- `bot-telemetry`: 自动化机器人遥测卡片 — 状态呼吸灯动画、执行指令计数、API 延迟指标
- `performance-metrics`: 业绩归因指标网格 — 胜率、最大回撤、盈亏比、夏普比率四宫格

### Modified Capabilities
_(无现有 specs 需要修改)_

## Impact

- **HTML**: `index.html` — `view-lifecycle` section (lines 398-454)，新增 HUD 区块、重构 report-metrics、新增 metrics-grid
- **CSS**: `style.css` — 新增 `.portfolio-hud`、`.bot-telemetry`、`.perf-metrics-grid` 及呼吸灯动画 keyframes
- **JS**: `js/views/portfolio.js` — 新增 `renderHUD()`、`renderBotTelemetry()`、`renderPerfMetrics()` 函数，扩展 mock data
- **Store**: `js/store/index.js` — `MOCK_DATA` 对象需扩展 HUD / telemetry / performance 相关字段
- **无后端 API 变更** — 本次变更全部为前端 UI 重构，使用 mock 数据
