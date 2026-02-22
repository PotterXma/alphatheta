## What

打通 "信号接收 → Toast → 路由跳转 → 策略自动组装 → 模拟盘结算 → 持仓更新" 全链路闭环。

## Why

$100k 空仓初始化已完成。系统需要一条从 Scanner 信号到实际建仓的数据流通路，才能让 Empty State 被真实持仓"破冰"。

## How (4 大能力)

### C1: 全局 Toast 通知 + 模拟触发器
- 新建 `js/components/signal-toast.js`
- 悬浮暗黑玻璃态 Toast (右上角)，含 Ticker + 推荐理由 + "⚡ 立即前往组装" 按钮
- `window.triggerMockSignal()` 控制台测试函数
- 对接后端 WebSocket `signal:new` 事件 (socketio)

### C2: 状态注入 + 智能路由
- Toast 按钮 click →
  1. `setGlobalTicker(payload.ticker)`
  2. `setState('pendingSignal', payload)` 暂存信号上下文
  3. `navigateTo('signal')` 跳转策略工作室
- 工作室 `onShow()` 检测 `pendingSignal` → 自动调用 `autoAssembleStrategy()`

### C3: 模拟盘结算引擎
- `executePaperTrade(legs)` →
  1. 计算 Net Debit/Credit
  2. 扣减 `MOCK_DATA.portfolio.cash`
  3. 构造持仓对象 push 进 `MOCK_DATA.activePositions`
  4. 更新 `MOCK_DATA.hud` (margin/delta/theta)
  5. 成功 Toast + `navigateTo('lifecycle')` 跳回跟踪页

### C4: 持仓页"破冰"渲染
- `portfolio.js` 的 `renderPositions()` 已有 empty-state vs 数据行逻辑
- 新持仓 push 后 `renderPositions()` 自动移除雷达空状态，渲染新行
- HUD 自动刷新 (renderHUD 读 MOCK_DATA.hud)

## Scope

- 前端 only，无后端改动
- 模拟盘结算纯前端计算 (Paper Trading)
- 后续接入真实 WebSocket 时只需替换 `triggerMockSignal` → `sio.on('signal:new')`

## Touchpoints

| 文件 | 角色 |
|------|------|
| `js/components/signal-toast.js` | **[NEW]** Toast UI + WS 监听 |
| `js/components/ui.js` | 复用 showToast |
| `js/main.js` | `navigateTo()` 路由 |
| `js/store/index.js` | `setState/getState` + MOCK_DATA |
| `js/views/strategy_studio.js` | `onShow` 检测 pendingSignal |
| `js/utils/strategy-generator.js` | `autoAssembleStrategy()` |
| `js/views/portfolio.js` | 持仓渲染 (已就绪) |
| `style.css` | Toast CSS 样式 |
