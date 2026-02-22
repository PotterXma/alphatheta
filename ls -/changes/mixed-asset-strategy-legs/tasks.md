## 1. Leg 数据结构 + 工厂函数

- [x] 1.1 在 `strategy_studio.js` 的 `createDefaultLeg()` 中增加 `type` 字段，默认 `"option"`
- [x] 1.2 新增 `createStockLeg(ticker, price, quantity = 100)` 工厂函数，返回 `{ type: "stock", multiplier: 1, right: null, strike: null, expiration: null, dte: null, ... }`

## 2. 智能组装注入 (Buy-Write)

- [x] 2.1 在 `strategy-generator.js` 新增 `generateShortOTMCall(spotPrice, calls, expiration)` — 寻找 Delta ≈ 0.16 OTM Call
- [x] 2.2 在 `autoAssembleStrategy()` 的 switch 中新增 `case "buy_write"` 分支，注入 STOCK 买入腿 + OTM Call 卖出腿
- [x] 2.3 修复 `autoAssembleStrategy()` L519 的 `totalBuy/totalSell` 计算，按 `type` 区分乘数

## 3. 成本引擎 (Paper Trade)

- [x] 3.1 重写 `paper-trade.js` L23 的成本计算：`const mult = leg.type === "stock" ? 1 : (leg.multiplier || 100)`
- [x] 3.2 重写持仓写入 (L46-62)：STOCK 腿写入 `type: "Stock"`，Option 腿根据 `right` 写入 `"Call"/"Put"`
- [x] 3.3 为所有腿分配统一 `orderId`，添加 `strategyGroup` 标签
- [x] 3.4 修复 HUD 估算 (L65-86)：STOCK 持仓不应计算 Theta，Delta = 1.0

## 4. 推荐卡片联动

- [x] 4.1 修改 `strategy_studio.js` 的 `onRecommendationCardClick()`：从推荐数据中读取 `stock_action`，当检测到 `buy_write` 时传递 `direction = "buy_write"` 给 `autoAssembleStrategy()`
- [x] 4.2 确保推荐卡片中的 `stock_action` 数据正确透传到组装函数

## 5. UI 渲染适配

- [x] 5.1 修改 `renderLegs()` 中腿列表 table row：对 `type === "stock"` 的行，Type 列显示 `STOCK` 徽章，Strike/Expiration/DTE 列显示 "—" 且禁用编辑
- [x] 5.2 修改 `updateLeg()` ：当 `type === "stock"` 时忽略 strike/expiration 字段更新

## 6. 验证

- [x] 6.1 手动测试：在 Strategy Studio 点击带 Buy-Write 建议的推荐卡片，确认生成 STOCK + CALL 双腿
- [x] 6.2 手动测试：验证 Net Debit 金额正确（正股 ×1，期权 ×100）
- [x] 6.3 手动测试：点击"模拟盘成交"，确认资金扣减正确、持仓包含 Stock + Call 记录
- [x] 6.4 手动测试：确认盈亏曲线图正确显示混合资产到期盈亏
