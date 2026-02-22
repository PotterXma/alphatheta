## ADDED Requirements

### Requirement: 操作按钮修复
每行持仓 SHALL 在操作列渲染两个暗黑玻璃微型按钮:
- `平仓` 按钮 (`.close-btn`) — hover 红色微光 `box-shadow`
- `展期` 按钮 (`.roll-btn`) — hover 青色微光 `box-shadow`

#### Scenario: 按钮交互
- **WHEN** 鼠标悬停操作按钮
- **THEN** 按钮显示对应颜色的微光效果

### Requirement: 方向数量列
每行持仓 SHALL 显示方向和数量: `买入 (Long) · 1张` (绿色) 或 `卖出 (Short) · 2张` (红色)。

#### Scenario: 买入方向
- **WHEN** 持仓方向为 "buy"
- **THEN** TD 显示 `买入 (Long) · 1张`，绿色强调

### Requirement: 盈亏双维展示
盈亏列 SHALL 同时显示绝对金额和百分比: `+$420.00 (+85.7%)`。正值绿色，负值红色，零值灰色。

#### Scenario: 正盈利
- **WHEN** PnL = +420, 初始成本 = 490
- **THEN** 显示 `+$420.00 (+85.7%)`，绿色

#### Scenario: 亏损
- **WHEN** PnL = -120, 初始成本 = 490
- **THEN** 显示 `-$120.00 (-24.5%)`，红色
