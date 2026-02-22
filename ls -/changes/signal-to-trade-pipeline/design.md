## Context

全链路: `triggerMockSignal()` / WS → Toast → `navigateTo('signal')` → Studio `autoAssembleStrategy()` → 用户确认 → `executePaperTrade()` → `navigateTo('lifecycle')` → 持仓渲染

已有基础设施:
- `showToast()` in `ui.js` (简单消息提示)
- `setGlobalTicker()` in `ui.js` (切换全局标的)
- `navigateTo(viewId)` in `main.js` (SPA 路由切换)
- `autoAssembleStrategy()` in `strategy-generator.js` (链数据 → 策略腿)
- `MOCK_DATA.activePositions` 数组 (portfolio.js 已支持 empty/data 双态渲染)

## Decisions

### D1: Toast 类型 — 新建 Signal Toast vs 复用 showToast

**选择**: 新建 `signal-toast.js` 独立组件

showToast 是 3s 自消失的简单消息，不支持 action 按钮。Signal Toast 是持久化的富通知卡片（有 ticker badge、推荐理由、CTA 按钮），需要独立 DOM + 手动关闭。两者共存不冲突。

### D2: 信号上下文传递 — URL params vs Store state

**选择**: `setState('pendingSignal', payload)` + Studio `onShow()` 消费

URL params 不适合复杂对象。Store 临时状态清晰、同步，Studio 消费后立即 `setState('pendingSignal', null)` 清除，避免误触。

### D3: 模拟盘结算 — 前端计算 vs API 调用

**选择**: 纯前端 `executePaperTrade(legs)` 计算

Paper Trading 模式下无需后端参与。直接从 legs 的 `ask/bid * quantity * 100` 算 Net Debit/Credit，扣减 `MOCK_DATA.portfolio.cash`。后续接入真实券商 API 时替换为 POST `/api/v1/orders/paper`。

### D4: 持仓对象结构 — 与 renderPositions 兼容

**选择**: 复用现有 position schema

```js
{
  ticker, type, typeCn, strike, expiry, dte,
  initialPremium, currentValue, pnl, quantity,
  action, // "buy" | "sell"
  openedAt: new Date().toISOString(),
}
```

这与 `renderPositions()` 模板中的字段完全对齐。

### D5: HUD 更新 — 手动计算 vs 重新渲染全部

**选择**: 直接修改 `MOCK_DATA.hud` 然后调 `renderHUD()`

Margin util = sum(position costs) / totalValue * 100。
Net Delta = 简化估算 (LEAPS Call ≈ 0.80 delta per contract)。
Net Theta = 简化估算 (LEAPS Call ≈ -$0.05/day per contract)。
