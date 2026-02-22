## Why

Top 3 推荐卡片当前通过 REST 一次性加载，用户必须手动刷新。后端的 WebSocket SIGNALS 频道(`/ws/feed?channels=signals`)和 Redis pub/sub 桥接已就绪，但前端未接入。期权信号时效性强——15 分钟前的推荐可能已不安全——需要自动保鲜机制。同时，用户正在操作卡片时数据闪跳会导致误下单。

## What Changes

- **WebSocket 信号流**: 新建 `js/services/signal-stream.js`，封装连接、重连、REST 补偿逻辑
- **防打扰状态机**: `isUserInteracting` 标志位 + 缓冲队列 + "新信号已到达" 发光徽章
- **信号 TTL 保鲜**: 每分钟检查 `captured_at`，超过 15 分钟标记 `.signal-stale`（变灰 + 禁用操作）
- **后端增强**: `/api/v1/dashboard/scan` 响应中为每个信号附加 `captured_at` 时间戳；WS broadcast 同样携带

## Capabilities

### New Capabilities
- `realtime-signal-stream`: WebSocket 信号订阅 + REST 补偿 + 防打扰锁定 + 信号 TTL 保鲜

### Modified Capabilities
_(无已有 spec 需要修改)_

## Impact

- **前端新文件**: `js/services/signal-stream.js`
- **前端修改**: `js/views/strategy_studio.js` (Top 3 面板接入信号流)
- **前端样式**: `style.css` (`.signal-stale`, `.badge-new-signal` 样式)
- **后端修改**: `app/routers/dashboard.py` (scan 响应添加 `captured_at`)
- **依赖**: 现有 `/ws/feed` + Redis pub/sub 桥接 (已就绪，无需改动)
