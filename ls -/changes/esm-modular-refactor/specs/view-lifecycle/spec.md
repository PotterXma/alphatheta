# View Lifecycle Spec

## Requirement: R1 — View Registry
`main.js` 维护 `Map<tabId, ViewModule>` 注册表。
每个 ViewModule 导出 `{ init(), onShow(), onHide() }` 三个生命周期钩子。

## Requirement: R2 — Tab Router
监听侧边栏 `.nav-item` 点击事件。
切换逻辑: 隐藏当前区块 → 显示目标区块 → 更新 `store.activeTab`。
CSS class `.active` 在导航项间切换。

## Requirement: R3 — ECharts Resize on Show
`onShow()` 中使用 `requestAnimationFrame(() => { chart?.resize() })` 唤醒 ECharts。
防止 ECharts 在 `display: none` 容器中初始化后宽度为 0px。
所有含 ECharts 的 view (dashboard, sandbox, portfolio) 必须实现此钩子。

## Requirement: R4 — Lazy Init
每个 view 的 `init()` 只在首次显示时调用一次。
`main.js` 用 `_initialized: Set<string>` 追踪，避免重复初始化。

## Requirement: R5 — 5 View Files
- `js/views/dashboard.js` — 仪表盘 (宏观雷达 + 信号引擎 + 持仓表 + Top Picks)
- `js/views/signal.js` — 信号与执行 (期权链 + 下单)
- `js/views/sandbox.js` — 策略沙盒 (BS P&L + Greeks)
- `js/views/portfolio.js` — 全程跟踪 (生命周期表 + 展期 Modal + 净值曲线)
- `js/views/settings.js` — 系统设置 (Watchlist CRUD + API Key + Kill Switch)

## Requirement: R6 — HTML Module Script
`index.html` 将 `<script src="app.js">` 替换为 `<script type="module" src="./js/main.js">`。
旧 `app.js` 暂保留为空壳，防止 404。
