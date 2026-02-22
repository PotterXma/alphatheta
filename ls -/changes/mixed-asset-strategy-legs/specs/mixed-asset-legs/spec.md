## ADDED Requirements

### Requirement: Mixed Asset Leg Data Structure
系统 SHALL 支持 `type: "stock"` 类型的腿，与 `type: "option"` 腿共存于 `currentLegs[]` 数组。
STOCK 腿 MUST 具有以下属性:
- `action`: `"buy"` 或 `"sell"`
- `type`: `"stock"`
- `right`: `null`
- `quantity`: 正整数 (通常 100 股)
- `price`: 当前正股价格
- `strike`: `null`
- `expiration`: `null`
- `dte`: `null`
- `multiplier`: `1` (固定值, 绝不为 100)

#### Scenario: STOCK leg created with correct defaults
- **WHEN** 系统创建一个 `type: "stock"` 的腿
- **THEN** `multiplier` MUST 为 `1`，`strike`/`expiration`/`dte`/`right` MUST 为 `null`

#### Scenario: Option leg retains existing behavior
- **WHEN** 系统创建一个 `type: "option"` 的腿
- **THEN** `multiplier` MUST 为 `100`，且 `right` MUST 为 `"call"` 或 `"put"`

---

### Requirement: Buy-Write Auto Assembly
当用户点击包含 Buy-Write 策略建议的推荐卡片时，`autoAssembleStrategy()` MUST 自动注入两条腿:
1. `{ action: "buy", type: "stock", quantity: 100, price: spotPrice, multiplier: 1 }`
2. `{ action: "sell", type: "option", right: "call", quantity: 1, price: premium, strike: OTM_strike, multiplier: 100 }`

#### Scenario: Buy-Write assembly produces stock + call legs
- **WHEN** 方向为 `"buy_write"` 且期权链中存在满足 Delta ≈ 0.16 的 OTM Call
- **THEN** `autoAssembleStrategy()` 返回 `legs` 数组包含恰好 2 条腿: 1 条 STOCK 买入 + 1 条 CALL 卖出

#### Scenario: Buy-Write cost calculation is correct
- **WHEN** SPY @ $500, OTM Call premium = $5.20, 组装 Buy-Write
- **THEN** 总净支出 MUST 为 `100 × $500 - 1 × $5.20 × 100 = $49,480`（正股不乘 100，期权乘 100）

#### Scenario: Buy-Write with no liquid call falls back
- **WHEN** 方向为 `"buy_write"` 但期权链无满足流动性的 OTM Call
- **THEN** 系统 SHALL 仅注入 STOCK 腿并在 `meta` 中标记 `"callUnavailable": true`

---

### Requirement: Mixed Cost Engine
成本引擎 MUST 按 `type` 区分乘数:
- **期权**: `cost = price × quantity × 100`
- **正股**: `cost = price × quantity × 1`
净成本 = 所有 BUY 腿总支出 − 所有 SELL 腿总收入。

#### Scenario: Net cost with mixed legs
- **WHEN** 组合包含 BUY STOCK 100 @ $200 和 SELL CALL 1 @ $5.00
- **THEN** 净成本 MUST 为 `(200 × 100 × 1) − (5.00 × 1 × 100) = $19,500`

#### Scenario: Multiplier is never applied to stock
- **WHEN** 任何包含 `type: "stock"` 腿的成本计算路径执行
- **THEN** 该腿的乘数 MUST 为 `1`，绝不为 `100`

---

### Requirement: Atomic Paper Trade Execution
`executePaperTrade()` MUST 将所有腿作为原子操作执行:
1. 验证可用资金 ≥ 净成本 (Net Debit)
2. 为所有腿分配统一的 `orderId`
3. 将 STOCK 腿写入持仓 (`type: "Stock"`)，Option 腿写入持仓 (`type: "Call"/"Put"`)
4. 一次性扣减总净成本

#### Scenario: Atomic execution succeeds
- **WHEN** 可用资金 $100,000，执行 Buy-Write (净成本 $49,480)
- **THEN** 资金扣减为 $50,520，持仓新增 2 条记录 (1 Stock + 1 Call)，共享同一 `orderId`

#### Scenario: Insufficient funds rejects entire order
- **WHEN** 可用资金 $10,000，执行 Buy-Write (净成本 $49,480)
- **THEN** 交易被拒绝，资金和持仓均不变

---

### Requirement: UI Stock Leg Rendering
当腿列表中包含 `type: "stock"` 腿时，UI MUST:
- Type 列: 显示 `STOCK` 标识 (替代 Call/Put 切换)
- Strike 列: 禁用输入，显示 "—"
- Expiration 列: 禁用输入，显示 "—"
- DTE 列: 显示 "—"
- Price/Quantity 列: 保持可编辑

#### Scenario: Stock leg renders correctly
- **WHEN** `currentLegs[]` 包含一条 `type: "stock"` 腿
- **THEN** 腿列表表格中该行 Strike 列显示 "—" 且不可编辑

#### Scenario: Stock leg coexists with option legs
- **WHEN** `currentLegs[]` 包含 1 条 STOCK 腿 + 1 条 CALL 腿
- **THEN** 两条腿均正确渲染，STOCK 行 Strike 为 "—"，CALL 行 Strike 为数值
