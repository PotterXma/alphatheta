## 1. 基础设施与依赖

- [x] 1.1 创建 `backend/app/services/market_calendar.py` — `isUSMarketOpen()` + `get_next_market_open()`
- [x] 1.2 创建 `backend/app/services/notification.py` — `NotificationManager` 骨架 (三通道)
- [x] 1.3 更新 `pyproject.toml` — 添加 `aiosmtplib`
- [x] 1.4 添加环境变量: `SERVERCHAN_SENDKEY`, `SMTP_HOST/USER/PASS`, `NOTIFY_EMAIL_TO`

## 2. 交易时间日历

- [x] 2.1 实现 `isUSMarketOpen()` — `zoneinfo.ZoneInfo("America/New_York")`, 工作日 09:30-16:00
- [x] 2.2 实现 `get_sleep_seconds()` — 闭市时计算距下一次检查应休眠的秒数
- [x] 2.3 实现 `sendDailyHeartbeat()` — 美东 09:20 推送进程存活 + Watchlist 数量 + Redis 状态

## 3. 两段式扫描引擎

- [x] 3.1 创建 `backend/app/services/scanner_daemon.py` — asyncio 主循环骨架
- [x] 3.2 实现冷却池 `AlertCooldown` — `dict[str, float]` + `is_cooled(ticker, direction)` + `mark(ticker, direction)`, 24h TTL
- [x] 3.3 阶段 1: 轻量初筛 — 获取 RSI/IVR, 随机延迟 1-3s, `RSI < 35 and IVR < 30` 过滤
- [x] 3.4 阶段 2: 重装深潜 — 冷却校验 → `findLeapsExpiration` → `validateLeapsLiquidity` → Deep ITM Call 寻址
- [x] 3.5 单标的 try-except 隔离 + API 重试 (3 次指数退避)
- [x] 3.6 信号结果格式化 + 触发 `NotificationManager.broadcast(signal)`

## 4. 多路消息网关

- [x] 4.1 实现 `sendWeChat(signal)` — Server酱 HTTP POST (`sctapi.ftqq.com/{SENDKEY}.send`)
- [x] 4.2 实现 `sendEmail(signal)` — aiosmtplib HTML 模板邮件
- [x] 4.3 实现 `broadcastToWeb(signal)` — python-socketio emit 到前端
- [x] 4.4 实现 `broadcast(signal)` — 并行调用三通道, 各自 try-except 隔离

## 5. 部署与集成

- [x] 5.1 创建 `backend/scanner_entry.py` — `asyncio.run(main())` 入口文件
- [x] 5.2 `docker-compose.yml` 新增 `scanner` 服务 (复用 api image, 不同 entrypoint)
- [x] 5.3 创建 `ecosystem.config.js` — PM2 配置 (max_memory_restart, 日志轮转)
- [ ] 5.4 端到端测试: 启动 scanner → 验证心跳推送 → 模拟初筛通过 → 验证微信收到信号
