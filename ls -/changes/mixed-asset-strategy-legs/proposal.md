## Why

全景策略工作室的智能组装器 (`autoAssembleStrategy`) 仅生成纯期权腿 (LEAPS Call/Put)，无法表达需要同时持有正股的混合策略 (Covered Call / Buy-Write)。`executePaperTrade` 对所有腿统一乘以 `multiplier: 100`，导致正股腿的资金计算出现 100 倍偏差。后端 `/dashboard/sync` 已返回 `stock_action` 字段告知用户正股操作，但前端无法将此建议转化为实际下单动作。

## What Changes

- **Leg 数据结构扩展**: 新增 `type: "STOCK"` 腿类型。当 `type === "STOCK"` 时，`strike`/`expiration`/`dte`/`right` 字段为 N/A，`multiplier` 固定为 `1`
- **智能组装注入**: `autoAssembleStrategy()` 在 `buy_write` 方向下自动 push 两条腿：`BUY STOCK 100 shares` + `SELL OTM Call 1 contract`
- **成本引擎重写**: `calculateNetPremium()` 和 `paper-trade.js` 中的成本计算按 `type` 区分乘数 — 期权 `×100`，正股 `×1`
- **原子模拟下单**: `executePaperTrade()` 将所有腿打上统一 `order_id`，正股写入正股持仓、期权写入期权持仓，资金一次性扣减
- **UI 渲染兼容**: 腿列表表格对 `STOCK` 类型行禁用行权价/到期日输入框，显示 "N/A"

## Capabilities

### New Capabilities
- `mixed-asset-legs`: 混合资产腿数据结构 + 智能组装 + 成本引擎 + 原子下单

### Modified Capabilities
_(无已有 spec 需要修改)_

## Impact

- **前端 JS 文件**:
  - `js/utils/strategy-generator.js` — `autoAssembleStrategy()` 新增 `buy_write` 分支
  - `js/services/paper-trade.js` — 重写成本计算 + 持仓写入逻辑
  - `js/views/strategy_studio.js` — 腿列表 UI 渲染适配 STOCK 类型
  - `js/utils/payoff-engine.js` — `legPayoff()` / `calculateNetPremium()` 已有 stock 支持 (无需改动)
- **后端**: 无需改动 (stock_action 已在 dashboard.py 返回)
- **数据**: `MOCK_DATA.activePositions` 数组新增 `type: "Stock"` 条目
- **风险**: 乘数计算错误会导致模拟盘资金偏差 100 倍，需重点测试
