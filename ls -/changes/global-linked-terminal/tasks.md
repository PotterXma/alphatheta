## 1. Backend — Top Picks API

- [x] 1.1 创建 `routers/advanced_ops.py`，注册到 FastAPI app (prefix `/api/v1/strategy`)
- [x] 1.2 实现 `GET /strategy/top-picks`: 查询 DB 活跃 + supports_options 标的列表
- [x] 1.3 并行调用 yfinance 获取 earningsDates，过滤未来 14 天内有财报的标的
- [x] 1.4 对通过排雷的标的并行获取 ATM premium yield (mid_price / spot_price)，降序取 Top 3
- [x] 1.5 返回结构化 JSON: `{ picks: [{ ticker, score, current_price, atm_premium, next_earnings, reasoning }] }`

## 2. Backend — 孤儿订单防护

- [x] 2.1 在 `settings.py` 的 `DELETE /watchlist/{ticker}` 中增加前置校验: 查询 orders 表 `WHERE ticker=X AND status IN ('pending','partial_fill','draft')`
- [x] 2.2 count > 0 时返回 HTTP 400 + 中文错误消息
- [x] 2.3 count == 0 时执行原有删除逻辑

## 3. Backend — 搜索 API

- [x] 3.1 在 `advanced_ops.py` 中新增 `GET /strategy/search?q=` — 用 yfinance 模糊匹配 ticker + 公司名
- [x] 3.2 返回 `[{ ticker, name, exchange }]` 格式，最多 8 条

## 4. Frontend — 全局标的状态

- [x] 4.1 在 `app.js` 中实现 `setGlobalTicker(ticker)` / `getGlobalTicker()` 函数，写入 `APP_STATE.globalActiveTicker` + sessionStorage
- [x] 4.2 页面加载时从 sessionStorage 恢复 `globalActiveTicker`，默认 "SPY"
- [x] 4.3 `setGlobalTicker` 触发 `window.dispatchEvent(new CustomEvent("ticker-changed", ...))`

## 5. Frontend — 防抖搜索下拉组件

- [x] 5.1 在 `app.js` 的 `WatchlistManager` 中添加 `_debounceTimer` 和 `_onSearchInput()` 方法 (300ms debounce)
- [x] 5.2 实现下拉菜单 DOM 渲染: `<div class="wl-dropdown">` 绝对定位、backdrop-filter: blur
- [x] 5.3 下拉项点击 → 调用 `addTicker()` → 关闭下拉
- [x] 5.4 点击外部 / Escape 关闭下拉
- [x] 5.5 添加下拉菜单的玻璃态 CSS 样式

## 6. Frontend — Signal 页 Top 3 推荐卡片

- [x] 6.1 在 `index.html` Signal 区域添加 Top 3 推荐卡片容器 HTML
- [x] 6.2 在 `app.js` 中实现 `TopPicksManager.fetchTopPicks()` + `renderCards()` 
- [x] 6.3 卡片点击事件 → 调用 `setGlobalTicker(ticker)` 实现跨页联动
- [x] 6.4 添加推荐卡片的玻璃态 CSS (含财报安全标记、premium yield 显示)

## 7. Frontend — 策略沙盒自动填充

- [x] 7.1 在 Sandbox 页初始化时读取 `getGlobalTicker()`，调用 API 获取 spot/ATM/premium
- [x] 7.2 自动填充 Strike / Premium 到表单输入框 + 动态添加 ticker option
- [x] 7.3 监听 `ticker-changed` 事件，ticker 切换时自动重新填充
- [x] 7.4 在 `index.html` Sandbox 区域添加 `<div id="payoff-chart-container">`
- [x] 7.5 添加 ECharts CDN 引用 + 基础初始化骨架代码

## 8. Frontend — 跨页联动集成

- [x] 8.1 全局 ticker badge 在 Signal 和 Sandbox 页 header 显示当前标的
- [x] 8.2 setGlobalTicker 同步更新所有 badge/label display

## 9. 验证

- [x] 9.1 Docker rebuild + API endpoints 测试 (search=200, top-picks=200, delete-guard=400/200)
- [x] 9.2 验证孤儿订单防护: DELETE 有 pending order → 400 拦截 ✅
- [x] 9.3 DB tables 创建: `watchlist_tickers` + `orders` (with orderstatus enum)
- [ ] 9.4 浏览器验证: 搜索防抖 + 下拉补全 + Top 3 推荐卡片 + 跨页联动
