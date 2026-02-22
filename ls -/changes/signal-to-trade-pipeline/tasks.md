## 1. Signal Toast 组件

- [x] 1.1 新建 `js/components/signal-toast.js` — Toast DOM 创建 + 显示/隐藏逻辑
- [x] 1.2 CSS: `.signal-toast` 暗黑玻璃态 + 右上角固定定位 + 入场/退场动画
- [x] 1.3 挂载 `window.triggerMockSignal(overrides?)` 全局测试函数
- [x] 1.4 在 `main.js` 中 import signal-toast 模块

## 2. 状态注入 + 路由

- [x] 2.1 Toast CTA click: `setGlobalTicker()` + `setState('pendingSignal', payload)` + `navigateTo('signal')`
- [x] 2.2 修改 `strategy_studio.js` `onShow()`: 检测 `pendingSignal` → 自动触发 `autoAssembleStrategy()`
- [x] 2.3 消费后 `setState('pendingSignal', null)` 清除

## 3. 模拟盘结算引擎

- [x] 3.1 新建 `js/services/paper-trade.js` — `executePaperTrade(legs)` 函数
- [x] 3.2 计算 Net Debit/Credit (sum of leg premium * quantity * multiplier)
- [x] 3.3 余额检查: netDebit > cash → 弹红色 Toast, return false
- [x] 3.4 扣减 `MOCK_DATA.portfolio.cash`, 更新 `totalValue`
- [x] 3.5 构造 position 对象, push 进 `MOCK_DATA.activePositions`
- [x] 3.6 更新 `MOCK_DATA.hud` (margin/delta/theta 简化计算)
- [x] 3.7 更新 `MOCK_DATA.perfMetrics.totalTrades += 1`
- [x] 3.8 成功 Toast + `navigateTo('lifecycle')`

## 4. Studio 集成

- [x] 4.1 修改 Studio "发送指令" 按钮: Paper 模式下调用 `executePaperTrade(currentLegs)`
- [x] 4.2 成功后自动路由回跟踪页

## 5. 验证

- [ ] 5.1 控制台 `triggerMockSignal()` → Toast 弹出, 点击 → Studio 自动组装
- [ ] 5.2 Studio 确认发送 → 扣减 cash → 跟踪页显示新持仓
- [ ] 5.3 HUD 非零, Empty State 消失
