## Context

AlphaTheta v2 全景策略工作室已支持多腿期权组装 (LEAPS Call/Put Spread)，但无法表达混合资产策略。
后端决策引擎已在 `stock_action` 字段中返回正股建议（Buy-Write / Covered Call），前端需要将建议转化为可执行腿。

**当前状态**:
- `payoff-engine.js` — `legPayoff()` 和 `calculateNetPremium()` 已有 `type === "stock"` 分支 ✅
- `strategy-generator.js` — `autoAssembleStrategy()` 仅生成纯期权腿 ❌
- `paper-trade.js` — 成本计算对所有腿应用 `multiplier: 100`，正股会偏差 100× ❌
- `strategy_studio.js` — UI 假设所有腿为 Call/Put，STOCK 腿无法渲染 ❌

## Goals / Non-Goals

**Goals:**
- 支持 `type: "STOCK"` 腿，与期权腿共存于 `currentLegs[]`
- `autoAssembleStrategy()` 在 `buy_write` 场景注入 STOCK + OTM Call 双腿
- 成本引擎正确区分正股 (`×1`) 和期权 (`×100`) 乘数
- `executePaperTrade()` 原子性写入混合持仓，统一 `order_id`
- UI 对 STOCK 腿禁用 strike/expiration/dte 字段

**Non-Goals:**
- 真实券商 API 对接 (仅模拟盘)
- 保证金引擎升级 (后续独立 change)
- 正股做空 (Short Stock) 场景
- T+1 结算规则模拟

## Decisions

### D1: Leg 数据结构 — 复用 `type` 字段

`payoff-engine.js` 已使用 `leg.type === "stock"` 进行分支，统一使用此约定：

```js
// STOCK leg
{ id, action: "buy", type: "stock", right: null, ticker, quantity: 100, price: spotPrice, strike: null, expiration: null, dte: null, multiplier: 1 }

// Option leg (现有)
{ id, action: "sell", type: "option", right: "call", ticker, quantity: 1, price: premium, strike, expiration, dte, multiplier: 100 }
```

**Rationale**: 保持与 `payoff-engine.js` 现有 stock 分支一致，无需改动盈亏曲线引擎。


### D2: 智能组装 — 新增 `buy_write` 分支

在 `autoAssembleStrategy()` 的 `switch(direction)` 中新增：

```
case "buy_write":
  legs = [
    { action: "buy", type: "stock", quantity: 100, price: spotPrice, multiplier: 1 },
    generateShortOTMCall(spotPrice, calls, expiration)  // Delta ≈ 0.16 OTM Call
  ]
```

**Rationale**: `buy_write` 来自后端 `stock_action` 字段，不是方向 (`bullish/bearish`)。需要新的入口或映射。
选择在推荐卡片点击时检测 `stock_action` 并注入，而非修改方向枚举。


### D3: 成本引擎 — 按 `type` 区分乘数

```js
const multiplier = leg.type === "stock" ? 1 : (leg.multiplier || 100);
const cost = leg.price * leg.quantity * multiplier;
```

此逻辑需统一应用到：
1. `calculateNetPremium()` — ✅ 已正确实现
2. `executePaperTrade()` — ❌ 需重写 (当前 L23 硬编码 `leg.multiplier || 100`)
3. `autoAssembleStrategy()` 的 `totalBuy/totalSell` 计算 — ❌ 需重写 (当前 L519 `l.price * l.multiplier * l.quantity`)


### D4: 原子下单 — 统一 `order_id`

```js
const orderId = `paper_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
for (const leg of legs) {
  position.orderId = orderId;
  position.strategyGroup = strategyLabel;  // "Buy-Write AAPL"
}
```

**Rationale**: positions 数组中打上 `orderId` 标签，后续可整组平仓/展示。


### D5: UI 渲染 — STOCK 腿特殊处理

腿列表中 STOCK 行：
- Type 列: 显示 `STOCK` 徽章 (replace CallPut toggle)
- Strike 列: 禁用输入，显示 "—"
- Expiration 列: 禁用输入，显示 "—"
- DTE 列: 显示 "—"
- Price 列: 仍可编辑 (用户可调整入场价)

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 乘数陷阱: 正股误乘 100 → 资金偏差 100× | 每个成本路径强制检查 `type → multiplier` 映射 |
| `stock_action` 字段仅在后端返回，前端推荐卡片点击时需传递 | 推荐卡片数据已含 `stock_action`，在 `onRecommendationCardClick` 中透传 |
| 盈亏曲线引擎假设 STOCK 腿数量级与期权不同 | `legPayoff()` 已正确处理，`calculateComboPayoff()` 的 priceRange 需验证 |
