## ADDED Requirements

### Requirement: HUD 空仓初始化
系统 SHALL 在无持仓时将 HUD 设为:
- Margin Utilization: `0%` (进度条宽度 0)
- Net SPY Delta: `0`
- Net Theta / Day: `$0.00`

#### Scenario: 初始加载
- **WHEN** 页面首次加载且无持仓
- **THEN** HUD 显示归零值而非 `--`

### Requirement: 绩效指标 N/A
系统 SHALL 在无交易历史时将 Win Rate / Max Drawdown / Profit Factor / Sharpe 统一显示为 `N/A` (暗灰色)。

#### Scenario: 零交易历史
- **WHEN** `completedTrades.length === 0`
- **THEN** 4 个绩效指标卡均显示 `N/A`

### Requirement: 遥测面板空状态
系统 SHALL 在空仓时显示:
- 信标: 绿色 (进程存活)
- 状态标签: "扫描中 · 0 指令"
- 今日执行指令: `0`
- 累计权利金: `$0.00`

#### Scenario: 遥测初始状态
- **WHEN** 无交易记录
- **THEN** 遥测面板显示归零值，信标保持绿色

### Requirement: Equity Curve 初始锚点
系统 SHALL 在 ECharts 初始化时设:
- 数据: `[[today, 100000]]` 单点
- markLine: y=100000 水平虚线，标签 "初始资金 $100K"

#### Scenario: 空仓图表
- **WHEN** 无历史净值数据
- **THEN** 图表显示 $100K 水平基准线

### Requirement: Equity 摘要归零
`equitySummary` 区块 SHALL 在空仓时可见，显示:
- 总收益: `$0.00 (0%)`
- 最大回撤: `0%`
- Sharpe: `N/A`

#### Scenario: 空仓摘要
- **WHEN** 无交易历史
- **THEN** 摘要区域显示归零值
