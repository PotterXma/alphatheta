## Why

AlphaTheta v2 目前是"静态单页面"架构：各视图独立渲染、无跨页状态、票池搜索无补全、新增标的无财报排雷、删除标的无持仓校验。这导致用户在 Signal 页看到推荐后，切到 Sandbox 或 Portfolio 还需重新手动选择标的，且可能误删有活跃仓位的标的产生"孤儿订单"。需要一次性将系统升级为全局联动的交互式金融终端。

## What Changes

- **新增后端 API**: `GET /api/v1/strategy/top-picks` — 遍历票池，排除未来14天有财报的标的 (防 IV Crush)，按 IV Rank / 权利金收益率降序返回 Top 3 推荐
- **强化删除安全**: `DELETE /api/v1/watchlist/{ticker}` 增加前置校验 — 检查该标的是否存在 Active 期权持仓/挂单，存在则拒绝删除 (HTTP 400)
- **新增前端搜索组件**: 票池管理页的添加输入框升级为带 300ms 防抖的下拉搜索补全 (Debounced Autocomplete)
- **新增全局状态管理**: 引入 `globalActiveTicker` 全局状态，Signal 页点击推荐 → 自动同步到 Sandbox / Portfolio / Lifecycle
- **重构策略沙盒**: 页面初始化时读取 `globalActiveTicker`，自动调用期权链 API 填充真实 Spot Price / ATM Premium，预留 Payoff Diagram 容器

## Capabilities

### New Capabilities
- `top-picks-api`: 智能推荐引擎 — 财报排雷 + IV Rank 排序 + Top 3 筛选
- `orphan-order-guard`: 孤儿订单防护 — 删除标的前校验活跃持仓/挂单
- `debounced-search`: 防抖搜索下拉组件 — 带毛玻璃效果的 Ticker 补全
- `global-ticker-state`: 跨页面全局标的联动 — Signal → Sandbox → Portfolio → Lifecycle 状态同步
- `sandbox-autofill`: 策略沙盒真实数据填充 — 期权链驱动 + Payoff Diagram 预留

### Modified Capabilities
- (无已有 spec 需修改)

## Impact

- **后端新增**: `routers/advanced_ops.py` (top-picks + orphan-guard), `adapters/yahoo.py` (earningsDates 获取)
- **后端修改**: `routers/settings.py` (DELETE 端点增加持仓校验)
- **前端修改**: `app.js` (全局状态 + 搜索组件 + 沙盒重构), `style.css` (下拉菜单玻璃态), `index.html` (推荐卡片 + payoff 容器)
- **API 路由**: `GET /strategy/top-picks`, 增强 `DELETE /settings/watchlist/{ticker}`
- **依赖**: yfinance (earningsDates), 现有 DB orders/positions 表 (持仓查询)
