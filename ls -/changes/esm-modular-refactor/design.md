# Design: ESM 模块化重构

## Architecture Overview

```
index.html
  └─ <script type="module" src="./js/main.js">
       ├─ js/store/index.js        ← Pub/Sub 状态机
       ├─ js/api/client.js         ← 统一 HTTP 拦截器
       ├─ js/api/services.js       ← 业务 API 调用
       ├─ js/components/ui.js      ← Toast / Modal
       ├─ js/utils/formatters.js   ← 纯函数 (formatMoney, etc.)
       ├─ js/utils/bs-engine.js    ← Black-Scholes 计算引擎
       └─ js/views/
            ├─ dashboard.js        ← "仪表盘" Tab
            ├─ signal.js           ← "信号与执行" Tab
            ├─ sandbox.js          ← "策略沙盒" Tab
            ├─ portfolio.js        ← "全程跟踪" Tab
            └─ settings.js         ← "系统设置" Tab
```

## D1: Pub/Sub State Machine (Proxy-based)

- 使用 `new Proxy()` 拦截 `state` 对象的 `set` 操作
- 内部维护 `Map<string, Set<Function>>` 订阅表
- `setState(key, value)` → Proxy `set` trap → 触发所有 `key` 的订阅者
- `subscribe(key, callback)` → 返回 `unsubscribe` 函数，防止内存泄漏
- **防坑**: 订阅回调用 `try/catch` 包裹，单个 subscriber 异常不影响其他

## D2: Unified HTTP Client (fetch wrapper)

- Base URL 自动拼接: `const BASE = window.location.origin`
- `AbortController` + 15s 默认超时 (可覆盖)
- Response 拦截:
  - `!response.ok` → throw `ApiError { status, statusText, url }`
  - `response.json()` 解析失败 → throw `ApiError { message: 'Invalid JSON' }`
- 导出 `get(path, opts)`, `post(path, data, opts)`, `del(path, opts)`
- **防坑**: `finally` 块 `clearTimeout`，防止 AbortController 泄漏

## D3: View Lifecycle + ECharts Resize

- `main.js` 维护 `views` 注册表: `Map<tabId, { init, onShow, onHide }>`
- Tab 切换流程:
  1. 当前 view `onHide()` → 暂停轮询/释放资源
  2. `display: none` 当前区块
  3. `display: block` 新区块
  4. 新 view `onShow()` → **关键**: `requestAnimationFrame(() => chart.resize())` 唤醒 ECharts
- **防坑**: ECharts 在 `display: none` 容器中 `init()` 后宽度为 0px。必须在 `onShow` 时 `resize()`。使用 `requestAnimationFrame` 确保 DOM 布局已完成。

## D4: Event Delegation

- 所有视图使用事件委托而非直接绑定
- 模式: `container.addEventListener('click', (e) => { const target = e.target.closest('[data-action]'); ... })`
- 每个 view 的 `init()` 只调用一次，不会因 re-render 重复绑定
- **防坑**: `e.target.closest()` 处理事件冒泡链，`.closest()` 返回 `null` 时安全跳过

## D5: Gradual Migration Strategy

- **Phase 1**: 创建 `store/index.js` + `api/client.js` (零破坏性，纯新增)
- **Phase 2**: 创建 `main.js` + 修改 `index.html` script 标签 (切入点)
- **Phase 3**: 逐个抽离 5 个 view 文件 (先 signal → dashboard → sandbox → portfolio → settings)
- **Phase 4**: 提取 components + utils (Toast, Modal, formatters, BS engine)
- **Phase 5**: 清空 `app.js`，全部迁移完成，删除旧文件
- 每个 Phase 结束后可独立验证，失败可回退

## D6: Nginx MIME Type

- 确保 nginx 配置中 `.js` 文件返回 `application/javascript`
- ES Module 的 `import` 语句要求 MIME 必须正确，否则浏览器拒绝加载
- 配置: `location ~* \.js$ { add_header Content-Type application/javascript; }`

## D7: MOCK_DATA 兼容层

- 当前 `app.js` 顶部定义了大量 `MOCK_DATA`，多个视图依赖
- 迁移策略: 在 `js/store/index.js` 中导出 `MOCK_DATA`，作为过渡层
- 最终目标: 各 view 从 API 获取数据，`MOCK_DATA` 逐步删除
