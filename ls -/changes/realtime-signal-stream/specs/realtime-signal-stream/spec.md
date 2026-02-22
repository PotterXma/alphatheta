## ADDED Requirements

### Requirement: WebSocket Signal Subscription
系统 SHALL 通过 WebSocket 连接 `/ws/feed?channels=signals` 实时接收 Top 3 信号更新。

#### Scenario: Initial connection establishes signal stream
- **WHEN** Strategy Studio 页面加载完成
- **THEN** 系统 MUST 建立 WebSocket 连接并注册信号监听，同时执行一次 REST `GET /api/v1/dashboard/scan` 获取初始快照

#### Scenario: Reconnection triggers REST compensation
- **WHEN** WebSocket 断线后重新连接成功
- **THEN** 系统 MUST 自动调用 `GET /api/v1/dashboard/scan` 补偿空窗期数据

#### Scenario: Exponential backoff on disconnect
- **WHEN** WebSocket 连接断开
- **THEN** 系统 SHALL 按 1s → 2s → 4s → ... → max 30s 间隔自动重连

---

### Requirement: Anti-Disturbance UI Lock
当用户正在与 Top 3 推荐区域交互时，系统 SHALL 暂存新信号而不直接更新 UI。

#### Scenario: User hovering prevents update
- **WHEN** 鼠标悬停在 Top 3 容器内且收到新信号
- **THEN** 新信号 MUST 存入缓冲队列，不更新卡片内容，并在标题旁显示 `✨ N 个新信号已到达` 发光徽章

#### Scenario: Active card prevents update
- **WHEN** 用户已点击某张推荐卡片（处于选中/操作状态）且收到新信号
- **THEN** 新信号 MUST 存入缓冲队列，不更新卡片内容

#### Scenario: Idle state applies pending signals
- **WHEN** 用户鼠标离开 Top 3 容器且无卡片处于选中状态，且缓冲队列中有待处理信号
- **THEN** 系统 SHALL 以 CSS transition 平滑替换卡片内容，并清除发光徽章

#### Scenario: Badge click forces refresh
- **WHEN** 用户点击 `✨ N 个新信号已到达` 发光徽章
- **THEN** 系统 SHALL 立即应用缓冲队列中的最新信号并清除徽章

---

### Requirement: Signal TTL Freshness
每张推荐卡片 MUST 携带 `captured_at` 时间戳，系统 SHALL 每 60 秒检查信号新鲜度。

#### Scenario: Fresh signal displays age
- **WHEN** `当前时间 - captured_at < 15 分钟`
- **THEN** 卡片右上角 MUST 显示 `⏱️ N min ago`

#### Scenario: Stale signal is grayed out
- **WHEN** `当前时间 - captured_at ≥ 15 分钟 (900000ms)`
- **THEN** 卡片 MUST 添加 `.signal-stale` 样式（降低透明度、灰度滤镜、禁用交互），并显示 `⚠️ 行情已过期，请谨慎操作`

#### Scenario: New signal replaces stale
- **WHEN** 收到新的信号更新且旧卡片已处于 stale 状态
- **THEN** 新信号 MUST 替换旧卡片并移除 `.signal-stale` 样式

---

### Requirement: Backend captured_at Timestamp
后端 `/api/v1/dashboard/scan` 响应和 WebSocket 信号广播 MUST 为每个信号包含 `captured_at` 字段（ISO 8601 UTC 时间戳）。

#### Scenario: Scan response includes captured_at
- **WHEN** 客户端请求 `GET /api/v1/dashboard/scan`
- **THEN** 响应中每个信号对象 MUST 包含 `captured_at` 字段，值为信号生成时的 UTC 时间戳
