# ESM 模块化重构

## Why
`app.js` 已膨胀至 2400+ 行，包含全局状态、API 请求、DOM 操作、ECharts 管理、视图路由等所有逻辑。
后续需要支撑多腿期权组合推演、自动化扫盘等复杂功能，单体架构已成为迭代瓶颈。
当前痛点：跨页面状态泄漏、ECharts 隐藏 Tab 渲染为 0px、fetch 散落无统一容错、事件重复绑定导致内存泄漏。

## What Changes
将 `app.js` 拆分为基于功能域的 ES6 Module 架构，引入 `<script type="module">` 加载方式。
保持暗黑玻璃态交互逻辑与 DOM 结构不变，重点在于代码解耦与规范化。

## Capabilities

### CAP-1: state-machine
轻量级 Pub/Sub 状态机 (`js/store/index.js`)。
维护 `activeTicker`, `isAutoTrading`, `lang` 等跨页面状态。
提供 `getState()`, `setState(key, value)`, `subscribe(key, callback)` 方法。
任何视图通过订阅实现联动，彻底解耦。

### CAP-2: http-client
统一 HTTP 拦截器 (`js/api/client.js`)。
自动拼接 Base URL、AbortController 超时、4xx/5xx 标准化 Error、`get/post/del` 便捷方法。
所有业务 API 调用收敛到 `js/api/services.js`。

### CAP-3: view-lifecycle
SPA 路由 + 视图生命周期管理 (`js/main.js`)。
侧边栏 Tab 切换时，按需触发 `onMount/onShow` 钩子。
核心防坑：ECharts 实例在隐藏 → 显示切换时自动 `chart.resize()`。
5 个独立视图控制器: `signal.js`, `sandbox.js`, `portfolio.js`, `settings.js`, `dashboard.js`。

### CAP-4: shared-components
跨页面复用 UI 组件 (`js/components/`)。
`Toast` (消息提示)、`Modal` (暗黑玻璃态弹窗)、格式化纯函数 (`formatMoney`, `formatPercentage`)。
事件委托绑定 DOM 操作，防止重复绑定内存泄漏。

## Impact
- **文件**: 新增 ~12 个 JS 文件，`app.js` 被拆解清空，`index.html` script 标签重写
- **Nginx**: 需确保 `.js` 文件的 MIME type 为 `application/javascript`
- **风险**: 渐进式迁移 — 每个 Phase 独立可验证，不会一次性破坏全部功能
