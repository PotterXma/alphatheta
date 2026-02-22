## Why

AlphaTheta v2 的 LEAPS 策略引擎已就绪，但当前只有被动触发 (用户点击推荐卡片)。缺少一个 7×24 小时主动扫描层来持续监控 Watchlist，在"黄金坑"出现时自动推送建仓信号。手动盯盘不可能覆盖 6-20 只标的的分钟级变化，需要一个工业级后台守护进程。

## What Changes

- **新增** `scanner_daemon` Python 模块 — 独立后台扫描进程
- **新增** `isUSMarketOpen()` — 美股交易时间日历 (EST/EDT, 09:30-16:00, 工作日)
- **新增** 两段式扫描循环 `scannerLoop()` — 轻量初筛 (RSI/IVR) + 重装深潜 (LEAPS 链)
- **新增** 24h 冷却池 `AlertCooldown` — 同一方向信号去重
- **新增** `NotificationManager` 多路消息网关 — WebSocket / Email / 微信 (Server酱/PushPlus)
- **新增** 开盘前心跳 `sendDailyHeartbeat()` — 09:20 EST 推送进程存活状态
- **新增** PM2/Systemd 部署配置

## Capabilities

### New Capabilities
- `market-calendar`: 美股交易时间判断 + 非交易时段休眠
- `two-stage-scanner`: 两段式扫描引擎 (轻量初筛 + 重装深潜 + 冷却池)
- `notification-gateway`: 多路消息网关 (WebSocket + Email + 微信)

### Modified Capabilities
_(无)_

## Impact

- **`backend/app/services/scanner_daemon.py`** [NEW] — 核心扫描守护进程
- **`backend/app/services/notification.py`** [NEW] — 多路消息网关
- **`backend/app/services/market_calendar.py`** [NEW] — 交易时间日历
- **`backend/docker-compose.yml`** — 新增 scanner 服务
- **`backend/requirements.txt`** — 新增 `pytz`, `python-socketio`, `aiosmtplib`, `httpx`
- **前端**: WebSocket Toast 弹窗 + 音效 (可后续迭代)
