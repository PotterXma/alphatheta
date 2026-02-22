## Phase 1: 核心基建 — 状态机与网络层

### 1.1 Store (js/store/index.js)
- [x] 1.1.1 创建 `js/store/` 目录
- [x] 1.1.2 实现 Proxy-based 响应式 state (activeTicker, isAutoTrading, lang, activeTab)
- [x] 1.1.3 实现 `getState(key)` / `setState(key, value)` 接口
- [x] 1.1.4 实现 `subscribe(key, callback)` → 返回 unsubscribe 函数
- [x] 1.1.5 订阅回调 try/catch 包裹，防止单个 subscriber 异常传播
- [x] 1.1.6 导出 MOCK_DATA 兼容层

### 1.2 HTTP Client (js/api/client.js)
- [x] 1.2.1 创建 `js/api/` 目录
- [x] 1.2.2 实现 `class ApiError extends Error` (status, statusText, url)
- [x] 1.2.3 实现 `request(method, path, opts)` — AbortController + 15s 超时 + response 拦截
- [x] 1.2.4 导出 `get(path)`, `post(path, data)`, `del(path)` 便捷方法
- [x] 1.2.5 `finally` 块保证 `clearTimeout`

### 1.3 API Services (js/api/services.js)
- [x] 1.3.1 提取 dashboard 相关: `fetchDashboardSync()`, `fetchMarketChart()`
- [x] 1.3.2 提取 strategy 相关: `fetchTopPicks()`, `searchTickers(q)`
- [x] 1.3.3 提取 order 相关: `fetchOrders()`, `submitOrder()`, `rollCombo()`
- [x] 1.3.4 提取 watchlist 相关: `fetchWatchlist()`, `addTicker()`, `removeTicker()`
- [x] 1.3.5 提取 portfolio 相关: `fetchEquityCurve()`
- [x] 1.3.6 提取 settings 相关: `fetchSettings()`, `updateSetting()`

---

## Phase 2: 入口路由与生命周期

### 2.1 Main Entry (js/main.js)
- [x] 2.1.1 创建 `js/main.js` — 导入 store + views
- [x] 2.1.2 实现 View 注册表: `Map<tabId, { init, onShow, onHide }>`
- [x] 2.1.3 实现 Tab Router: 侧边栏 `.nav-item` 点击 → 切换 section display + active class
- [x] 2.1.4 实现 lazy init: `_initialized Set` 追踪首次显示
- [x] 2.1.5 实现 `onShow()` 钩子: `requestAnimationFrame(() => chart?.resize())` 唤醒 ECharts
- [x] 2.1.6 实现 `onHide()` 钩子: 暂停轮询 / 释放资源

### 2.2 HTML 升级 (index.html)
- [x] 2.2.1 替换 `<script src="app.js">` 为 `<script type="module" src="./js/main.js">`
- [x] 2.2.2 移除旧 `app.js` 中所有 `DOMContentLoaded` 逻辑 (迁移到 main.js)
- [x] 2.2.3 确保 ECharts CDN `<script>` 在 module script 之前加载

---

## Phase 3: 视图控制器抽离

### 3.1 Dashboard View (js/views/dashboard.js)
- [x] 3.1.1 迁移宏观雷达卡片渲染 (VIX/SPY/QQQ)
- [x] 3.1.2 迁移信号引擎面板渲染
- [x] 3.1.3 迁移持仓表渲染 + 事件委托
- [x] 3.1.4 迁移 TopPicksManager → dashboard view 调用 api/services
- [x] 3.1.5 导出 `initDashboardView()` / `onShow()` / `onHide()`

### 3.2 Signal View (js/views/signal.js)
- [x] 3.2.1 迁移期权链表格渲染
- [x] 3.2.2 迁移下单/批量操作逻辑
- [x] 3.2.3 订阅 `store.activeTicker` → 联动刷新
- [x] 3.2.4 事件委托绑定所有按钮操作
- [x] 3.2.5 导出 `initSignalView()` / `onShow()` / `onHide()`

### 3.3 Sandbox View (js/views/sandbox.js)
- [x] 3.3.1 迁移 PayoffChartManager (ECharts 双曲线)
- [x] 3.3.2 迁移 DTE/IV 滑块监听 + recalcAll()
- [x] 3.3.3 迁移 Greeks 面板 DOM 更新
- [x] 3.3.4 引入 `bs-engine.js` 计算模块
- [x] 3.3.5 导出 `initSandboxView()` / `onShow()` (含 chart.resize())

### 3.4 Portfolio View (js/views/portfolio.js)
- [x] 3.4.1 迁移生命周期表渲染
- [x] 3.4.2 迁移 RollManager (展期 Modal)
- [x] 3.4.3 迁移 EquityCurveManager (ECharts 净值曲线)
- [x] 3.4.4 导出 `initPortfolioView()` / `onShow()` (含 chart.resize())

### 3.5 Settings View (js/views/settings.js)
- [x] 3.5.1 迁移 WatchlistManager (CRUD + 防抖搜索)
- [x] 3.5.2 迁移 API Key 管理
- [x] 3.5.3 迁移 Kill Switch 配置
- [x] 3.5.4 导出 `initSettingsView()` / `onShow()`

---

## Phase 4: 全局公共组件与工具提取

### 4.1 UI Components (js/components/ui.js)
- [x] 4.1.1 提取 `showToast(message, type)` — 全局消息提示
- [x] 4.1.2 提取 `openModal(id)` / `closeModal(id)` — 暗黑玻璃态弹窗
- [x] 4.1.3 提取 `setGlobalTicker(ticker)` — store + UI 联动

### 4.2 Formatters (js/utils/formatters.js)
- [x] 4.2.1 提取 `formatMoney(num)`, `formatPercentage(num)`
- [x] 4.2.2 提取 `formatDate(str)`, `formatDelta(num)`
- [x] 4.2.3 提取 i18n 翻译 `t(key)` 函数

### 4.3 BS Engine (js/utils/bs-engine.js)
- [x] 4.3.1 提取 `BlackScholesEngine` 对象 (normalCDF, bsPrice, 4 Greeks)
- [x] 4.3.2 导出为独立 ESM 模块

---

## Phase 5: 清理与验证

### 5.1 清理
- [x] 5.1.1 清空 `app.js` (保留空壳防 404)
- [x] 5.1.2 验证 nginx MIME type 配置 (.js → application/javascript) ✅ curl 200 OK

### 5.2 验证
- [ ] V1 Dashboard Tab: 宏观雷达 + 信号引擎 + 持仓表 + Top Picks 渲染正常
- [ ] V2 Signal Tab: 期权链加载 + 下单功能正常
- [ ] V3 Sandbox Tab: DTE/IV 滑块 → 双曲线实时重绘 + Greeks 更新
- [ ] V4 Portfolio Tab: 生命周期表 + 展期 Modal + 净值曲线
- [ ] V5 Settings Tab: Watchlist CRUD + 搜索防抖
- [ ] V6 跨 Tab 切换: ECharts 图表不出现 0px 宽度
- [ ] V7 全局联动: 切换 Ticker → 所有订阅视图联动刷新
