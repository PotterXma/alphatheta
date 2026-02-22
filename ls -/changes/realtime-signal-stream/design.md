## Context

后端 `/ws/feed?channels=signals` 已通过 Redis pub/sub 桥接信号，前端未接入。
`loadRecommendations()` 在 `strategy_studio.js:183` 做一次性 `GET /api/v1/dashboard/scan`。
`strategy_studio.js:921` 只在页面初始化时调用一次 `loadRecommendations()`。

## Goals / Non-Goals

**Goals:**
- 前端通过 WebSocket 实时接收 Top 3 信号更新
- 断线重连时自动 REST 补偿（防空窗期丢失）
- 用户交互时暂存更新，离开后平滑替换（防打扰）
- 信号超过 15 分钟自动灰化 + 禁用操作（TTL 保鲜）

**Non-Goals:**
- 修改后端 WS 协议或 Redis pub/sub 架构
- 实现推送通知 / 声音提醒
- 支持多页面间的信号同步

## Decisions

### D1: 信号流服务 — 独立模块 `signal-stream.js`

封装 WebSocket 连接管理到 `js/services/signal-stream.js`:
- `connect()` → 连接 `/ws/feed?channels=signals`
- `onSignal(callback)` → 注册回调
- 自动重连 (exponential backoff: 1s → 2s → 4s → max 30s)
- 重连后自动 REST `GET /api/v1/dashboard/scan` 补偿

**Rationale**: 解耦信号传输层与 UI 层，未来 dashboard.js 也能复用。


### D2: 防打扰 — hover + active 双触发锁

```
isUserInteracting = mouseInTop3Container || activeCardTicker !== null
```

- `true` → 新数据存入 `pendingSignals[]`，显示徽章 `✨ N 个新信号`
- `false` → 立即应用 `pendingSignals`，CSS transition 平滑替换
- 用户点击徽章 → 强制刷新
- 用户离开容器 (mouseleave) + 无 active card → 自动 flush

**Rationale**: hover 检测防止卡片在鼠标下闪跳，active 检测防止正在操作的卡片被替换。

### D3: TTL 机制 — 每 60s 检查 `captured_at`

```
age = Date.now() - captured_at
if (age > 900_000) → .signal-stale (灰化 + 禁用)
else → 显示 "⏱️ N min ago"
```

- `captured_at` 由后端在 scan 响应和 WS broadcast 中携带（ISO 时间戳）
- 前端使用 `setInterval(checkSignalFreshness, 60_000)` 定时器
- `.signal-stale` 样式: `opacity: 0.45; filter: grayscale(80%); pointer-events: none`

### D4: 后端 `captured_at` 注入

在 `dashboard.py` 的 `_scan_single()` 返回值中添加:
```python
"captured_at": datetime.now(timezone.utc).isoformat()
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| WS 频繁推送导致 DOM 抖动 | 防打扰锁 + 100ms debounce |
| 断网时 pendingSignals 堆积 | REST 补偿覆盖全量数据，不做增量合并 |
| `setInterval` 页面后台时不精确 | `checkSignalFreshness()` 使用绝对时间差，不依赖间隔精度 |
