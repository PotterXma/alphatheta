## Context

AlphaTheta v2 前端已完成 ESM 模块化重构 (Phase 1-4)，架构支持 View Controller 生命周期管理、Proxy-based 响应式状态、以及统一 HTTP 客户端。当前 Signal 页面只支持单腿期权推荐，无法表达 Iron Condor、Calendar Spread 等多腿组合。

后端已有 `/api/v1/dashboard/sync` (行情同步) 和 `/api/v1/strategy/signal` (AI 信号)，但缺乏按 Ticker+到期日查询期权链的能力。

## Goals / Non-Goals

**Goals:**
- 用户可自由组装任意多腿期权组合（包含正股腿），不限策略类型
- 一键加载预设策略模板（Buy-Write, Iron Condor, Calendar Spread 等）
- 实时通用盈亏推演：不依赖硬编码公式，纯分段线性扫描
- 迷你期权链面板：T 型报价，点击填入 strike + price
- 情景推演卡片：Max Profit / Max Loss / Break-even / Est. Collateral

**Non-Goals:**
- Greeks 实时流动（留给后续迭代，当前只做到期日内在价值）
- 真实 margin 计算（使用 Max Loss 近似 Est. Collateral）
- 多腿组合的后端持久化（本期纯前端状态，不入库）
- IV 曲面 / Skew 可视化

## Decisions

### D1: 多腿状态数组 — `currentLegs[]` 作为唯一数据源

**决策**: 维护全局数组 `currentLegs`，每条 Leg 结构:

```js
{
  id: crypto.randomUUID(),        // 唯一标识，用于 DOM diff
  type: 'option' | 'stock',       // 腿类型
  right: 'call' | 'put' | null,   // 期权方向 (stock 为 null)
  action: 'buy' | 'sell',         // 买/卖
  expiration: '2026-04-15',       // 到期日 (stock 为 null)
  strike: 520,                    // 行权价 (stock 时为买入价)
  quantity: 1,                    // 合约数
  price: 3.80,                    // 盘口价 (期权权利金 / 股票价格)
  multiplier: 100 | 1,            // 期权=100, 股票=1
}
```

**Why**: 单一数据源驱动渲染 + 盈亏计算，避免 DOM ↔ 状态不同步。任何 UI 变更先更新数组，再触发 `renderLegs()` + `recalcPayoff()` 级联刷新。

**Alternatives considered**: Proxy per-leg → 过度复杂，`Map<id, leg>` → 丢失顺序。

### D2: 通用盈亏引擎 — 分段线性扫描算法

**决策**: `calculateComboPayoff(legs, spotPrice)` 纯函数，零 DOM 依赖。

算法:
1. 生成测试区间 `[spot * 0.5, spot * 1.5]`，步长 `$0.1` → ~1000 个价格点
2. 对每个模拟价格 $S$，遍历 `legs`，叠加每条腿的到期盈亏:
   - **Call 买方**: `(max(0, S - K) - premium) × qty × mult`
   - **Call 卖方**: `(premium - max(0, S - K)) × qty × mult`
   - **Put 买方**: `(max(0, K - S) - premium) × qty × mult`
   - **Put 卖方**: `(premium - max(0, K - S)) × qty × mult`
   - **Stock 买方**: `(S - price) × qty × 1`
   - **Stock 卖方**: `(price - S) × qty × 1`
3. 特征提取:
   - `maxProfit` = max(pnlArray)，若在边界 → "Unlimited"
   - `maxLoss` = min(pnlArray)，若在边界 → "Unlimited Risk"
   - `breakevens` = 扫描 pnlArray 中相邻正负符号翻转点，线性插值精确定位

**Why**: 通用算法自动处理任何腿数组合（1 腿到 10 腿），无需为每种策略写公式。精确到 $0.1 步长对 UI 展示足够。

**Alternatives considered**: 解析法求 breakeven → 多腿时无闭式解; BS 实时定价 → 本期只做到期日内在价值。

### D3: 迷你期权链 — 就地展开 T 型报价面板

**决策**: 点击 Leg 的行权价输入框 → 异步 fetch `/api/v1/market/option_chain_mini?ticker=XXX&date=YYYY-MM-DD` → 在输入框下方渲染毛玻璃浮层，左列 Call Bid/Ask，右列 Put Bid/Ask，中间列 Strike。点击 Bid/Ask 格子自动填入该 Leg 的 `strike` + `price`。

**数据缓存**: 同一 ticker+date 组合缓存 30s (Map<key, {data, ts}>)，避免重复调用 yfinance。

### D4: 策略模板 — 后端预配置 JSON

**决策**: 后端 `/api/v1/strategy/templates` 返回模板数组，每个模板包含 `legs[]` 骨架（相对行权价偏移量 `strikeOffset`, 默认 DTE 等）。前端加载模板时根据当前 activeTicker 的现价计算绝对行权价，覆写 `currentLegs`。

模板示例 (Iron Condor):
```json
{
  "name": "Iron Condor",
  "description": "市场中性策略，同时卖出 OTM Call 和 OTM Put",
  "legs": [
    { "type":"option", "right":"put",  "action":"buy",  "strikeOffset":-20, "qty":1 },
    { "type":"option", "right":"put",  "action":"sell", "strikeOffset":-10, "qty":1 },
    { "type":"option", "right":"call", "action":"sell", "strikeOffset":+10, "qty":1 },
    { "type":"option", "right":"call", "action":"buy",  "strikeOffset":+20, "qty":1 }
  ]
}
```

### D5: 后端期权链 API — yfinance + 精简输出

**决策**: 新增 `app/routers/market_data.py`，使用 `yfinance.Ticker(ticker).option_chain(date)` 获取 calls/puts DataFrame，过滤现价 ±5 档，只返回 `strike, bid, ask, lastPrice, volume, openInterest`。

**Error handling**: yfinance 超时 → 504; 无有效日期 → 400 + 可用日期列表; 无数据 → 空数组 + message。

### D6: Net Premium 计算 — 实时遍历

```
Net = Σ(sell legs: price × qty × mult) - Σ(buy legs: price × qty × mult)
```
Net > 0 → "Net Credit" (绿色), Net < 0 → "Net Debit" (红色)。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| yfinance 延迟 / rate limit | 前端缓存 30s; 后端加 Redis TTL 60s 缓存 |
| 大量 Legs (>10) 导致 DOM 抖动 | `requestAnimationFrame` 批量 DOM 更新 |
| 盈亏曲线步长 0.1 对低价股过粗 | 自适应步长: `spot * 0.001` (保证 ~1000 点) |
| 用户输入无效组合 (如 0 quantity) | 引擎忽略 qty=0 的腿; UI 显示警告 |
| 旧 Signal 页面兼容 | Tab ID 保持 `signal`，只替换内部 DOM + 逻辑 |
