## ADDED Requirements

### Requirement: Signal Toast 通知
系统 SHALL 在收到信号时显示持久化 Toast 通知，包含:
- Ticker 徽标 (大字体, 青色)
- 推荐理由文本
- "⚡ 立即前往组装" CTA 按钮 (青色发光)
- 手动关闭 × 按钮

#### Scenario: 信号到达
- **WHEN** WebSocket 收到 `signal:new` 或调用 `triggerMockSignal()`
- **THEN** 右上角显示暗黑玻璃态 Signal Toast，5s 后不自动消失

#### Scenario: 点击 CTA
- **WHEN** 用户点击 "立即前往组装"
- **THEN** Toast 关闭, 全局标的切换为信号 ticker, 路由至策略工作室

---

### Requirement: 控制台模拟触发器
系统 SHALL 在 `window` 上挂载 `triggerMockSignal(overrides?)` 函数:
- 默认 Payload: `{ ticker: 'AAPL', type: 'LEAPS_CALL', dte: 365, reason: 'RSI 超卖且 IVR 极低' }`
- 支持 override 任意字段

#### Scenario: 控制台触发
- **WHEN** 开发者在 console 执行 `triggerMockSignal()`
- **THEN** Signal Toast 弹出，等同于真实 WS 信号

---

### Requirement: 策略工作室自动组装
系统 SHALL 在工作室 `onShow` 时检测 `pendingSignal`:
- 若存在 → 自动设置 ticker、调用 `autoAssembleStrategy()`
- 消费后清除 `pendingSignal`

#### Scenario: 自动组装
- **WHEN** 从 Toast 路由到 Studio 且 pendingSignal = AAPL LEAPS_CALL
- **THEN** 工作室自动组装 AAPL LEAPS Call 策略，显示 P/L 曲线

---

### Requirement: 模拟盘结算
系统 SHALL 提供 `executePaperTrade(legs)` 函数:
- 计算 Net Debit/Credit
- 从 cash 中扣减
- 构造 position 对象 push 进 activePositions
- 成功 Toast + 路由回跟踪页

#### Scenario: Paper Trade 执行
- **WHEN** 用户在 Studio 确认发送指令 (Paper 模式)
- **THEN** cash 扣减, 新持仓写入, HUD 更新, 跳转跟踪页

#### Scenario: 余额不足
- **WHEN** Net Debit > cash
- **THEN** 弹出红色 Toast "购买力不足", 不执行

---

### Requirement: 持仓页破冰
系统 SHALL 在新持仓写入后自动:
- 移除 Empty State (雷达动效)
- 渲染新持仓行 (含操作按钮)
- 更新 HUD (margin/delta/theta)
- 更新 perfMetrics (totalTrades + 1)

#### Scenario: 首笔建仓
- **WHEN** executePaperTrade 成功, activePositions 从 0 变为 1
- **THEN** 跟踪页显示 1 行持仓, HUD 显示非零值
