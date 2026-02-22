## 1. 后端: captured_at 注入

- [x] 1.1 在 `dashboard.py` 的 `_scan_single()` 返回值中添加 `"captured_at": datetime.now(timezone.utc).isoformat()`
- [x] 1.2 在 `dashboard.py` 的 `/sync` signal_data 中添加同样的 `captured_at`

## 2. 前端: 信号流服务 (`signal-stream.js`)

- [x] 2.1 创建 `js/services/signal-stream.js`，封装 WebSocket 连接到 `/ws/feed?channels=signals`
- [x] 2.2 实现 exponential backoff 自动重连 (1s → 2s → 4s → max 30s)
- [x] 2.3 实现 `onReconnect` / `onOpen` 时自动 REST `GET /api/v1/dashboard/scan` 补偿
- [x] 2.4 暴露 `onSignal(callback)` 注册回调 + `connect()` / `disconnect()` API

## 3. 前端: 防打扰状态机

- [x] 3.1 在 `strategy_studio.js` 中添加 `isUserInteracting` 状态变量 (hover + active card 联合检测)
- [x] 3.2 Top 3 容器绑定 `mouseenter/mouseleave` 事件更新 `isUserInteracting`
- [x] 3.3 实现缓冲队列 `pendingSignals[]`：当 `isUserInteracting === true` 时暂存新数据
- [x] 3.4 实现发光徽章 `✨ N 个新信号已到达 (点击刷新)` — 在 Top 3 标题旁动态显示
- [x] 3.5 实现 flush 逻辑: mouseleave + 无 active card → CSS transition 平滑替换 + 清除徽章

## 4. 前端: 信号 TTL 保鲜

- [x] 4.1 实现 `checkSignalFreshness()` 定时器 (每 60s 执行一次)
- [x] 4.2 卡片右上角动态显示 `⏱️ N min ago` 相对时间
- [x] 4.3 超过 15 分钟 (900000ms) 的卡片添加 `.signal-stale` 样式 + `⚠️ 行情已过期` 文案

## 5. CSS 样式

- [x] 5.1 添加 `.signal-stale` 样式: `opacity: 0.45; filter: grayscale(80%); pointer-events: none`
- [x] 5.2 添加 `.badge-new-signal` 发光徽章样式 (极客风 glow animation)
- [x] 5.3 添加卡片替换时的 CSS transition (fade + slide)

## 6. 集成与接入

- [x] 6.1 在 `strategy_studio.js` 初始化时调用 `signal-stream.js` 的 `connect()`，并注册信号回调到防打扰状态机
- [x] 6.2 重构 `loadRecommendations()` 为可复用的 `renderSignals(signals)` — 供 REST 和 WS 共用

## 7. 验证

- [x] 7.1 手动测试: 刷新页面，确认 Top 3 卡片加载且显示 `⏱️ 0 min ago`
- [x] 7.2 手动测试: 等待 1 分钟，确认时间标签更新为 `⏱️ 1 min ago`
- [x] 7.3 手动测试: hover 到 Top 3 区域时确认新信号不会替换卡片，离开后自动刷新
- [x] 7.4 手动测试: 断开/恢复网络，确认 WS 重连后自动获取最新数据
