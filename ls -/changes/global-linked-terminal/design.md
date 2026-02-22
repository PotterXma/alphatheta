## Context

AlphaTheta v2 是 SPA 单文件架构 (index.html + app.js + style.css)，后端 FastAPI + PostgreSQL + yfinance。当前各页面独立渲染，无跨页状态共享。票池管理已实现 DB-backed CRUD (`settings.py`)，策略引擎已有 `evaluate_market_entry` + 期权链。需要在此基础上叠加全局联动能力。

## Goals / Non-Goals

**Goals:**
- 后端: Top 3 推荐 API (财报排雷 + IV Rank)、删除前持仓校验
- 前端: 防抖搜索下拉、全局标的状态、沙盒自动填充
- 所有交互保持暗黑玻璃态一致性

**Non-Goals:**
- 不做 WebSocket 实时推送 (仍用 polling / on-demand)
- 不做完整的 Payoff Diagram 交互 (仅预留容器 + 骨架)
- 不做 React/Vue 迁移 (保持原生 JS)

## Decisions

### D1: Top Picks API — 财报排雷算法

**选择**: `GET /api/v1/strategy/top-picks` 在新文件 `routers/advanced_ops.py` 中实现
**流程**:
1. 从 DB 查询所有 `is_active=True` 且 `supports_options=True` 的标的
2. 并行调用 `yfinance` 获取每只标的的 `earningsDates`
3. 排除未来 14 天内有财报的标的 (IV Crush 风险)
4. 对剩余标的计算 IV Rank 或 ATM premium yield
5. 降序取 Top 3 返回

**替代方案**: 在前端过滤 → 不可行，前端无法访问 earningsDates
**理由**: 后端一次性完成排雷 + 排序，前端只需渲染

### D2: 孤儿订单防护 — DELETE 前置校验

**选择**: 增强 `settings.py` 的 `DELETE /watchlist/{ticker}` 端点
**逻辑**: 删除前查询 `orders` 表中 `ticker=X AND status IN ('pending','partial_fill','active')` 的记录数
- count > 0 → HTTP 400 + 错误消息
- count == 0 → 允许删除

**替代方案**: 新建独立端点 → 破坏 RESTful 语义
**理由**: 校验逻辑属于删除操作的前置条件，应内嵌在 DELETE handler 中

### D3: 防抖搜索 — 前端实现

**选择**: 在 `WatchlistManager` 中扩展，将 Quick Add 输入框升级为 autocomplete
**架构**:
```
input[300ms debounce] → GET /api/v1/strategy/search?q=AAP
                      → dropdown overlay (backdrop-filter: blur)
                      → click → POST /settings/watchlist
```

**后端搜索端点**: `GET /api/v1/strategy/search?q=` — 查询 yfinance `Ticker.info` 匹配
**替代方案**: 前端预加载完整股票列表 → 数据量太大 (>8000 tickers)
**理由**: 按需查询更轻量，且能获取公司全名

### D4: 全局标的状态 — Vanilla JS 模式

**选择**: 用 `APP_STATE.globalActiveTicker` + 自定义事件 `ticker-changed`
**API**:
```javascript
function setGlobalTicker(ticker) {
  APP_STATE.globalActiveTicker = ticker;
  window.dispatchEvent(new CustomEvent("ticker-changed", { detail: { ticker } }));
}
// 各页面监听:
window.addEventListener("ticker-changed", (e) => { ... });
```

**替代方案**: React Context / Zustand → 需要框架迁移
**理由**: 当前项目是原生 JS SPA，CustomEvent 是零依赖方案

### D5: 沙盒自动填充 — 期权链驱动

**选择**: Sandbox 页面监听 `ticker-changed`，自动调用 `/dashboard/sync?ticker={t}` 获取当前价格 + ATM 期权数据
**填充字段**: Spot Price → 输入框, ATM Strike → 近月平值, Premium → mid price
**Payoff 容器**: `<div id="payoff-chart-container">` + ECharts CDN 基础初始化

## Risks / Trade-offs

- **[Risk] yfinance earningsDates 不稳定**: 部分标的返回空 → Mitigation: earningsDates 为空视为"不在财报窗口"，允许通过
- **[Risk] 搜索 API 延迟**: yfinance search 可能 1-2s → Mitigation: 前端显示 loading spinner + 300ms debounce 减少请求
- **[Risk] 全局状态丢失**: 刷新页面后 `globalActiveTicker` 重置 → Mitigation: 写入 `sessionStorage`，页面加载时恢复
