## Context

AlphaTheta v2 后端已有:
- Redis 缓存层 (expirations 24h TTL, option_chain 4h TTL)
- yfinance 适配器 (`YahooFinanceAdapter`) — 行情/指标/期权链
- Watchlist DB 模型 (`WatchlistTicker`)
- LEAPS 前端引擎 (`strategy-generator.js`) — 但仅被动触发

需要新增独立 Python 守护进程，与现有 FastAPI app 共享 DB/Redis 但独立运行 (非 FastAPI 路由)。

## Goals / Non-Goals

**Goals:**
- 7×24 守护进程，交易时段每 15 分钟扫描 Watchlist
- 美东时区感知 (EST/EDT 自动切换, DST 安全)
- 两段式扫描减少 API 调用量 (初筛 → 深潜)
- 24h 信号冷却去重
- 三通道推送: WebSocket / Email / 微信
- 崩溃隔离: 单标的异常不影响全循环

**Non-Goals:**
- 不做自动下单 (只推信号)
- 不做前端 WebSocket Toast UI (本轮只做后端推送管道)
- 不做盘后/盘前延长交易时段扫描

## Decisions

### D1: 进程模型 — 独立 asyncio 进程 vs Celery Beat

**选择**: 独立 `asyncio.run()` 进程 + PM2 守护

Celery Beat 过重 (依赖 broker, 序列化开销)。Scanner 只需一个单进程无限循环 + `asyncio.sleep`。PM2 负责崩溃自动重启 + 日志轮转。

### D2: 时区处理 — pytz vs zoneinfo

**选择**: Python 3.9+ 标准库 `zoneinfo` (零依赖)

`zoneinfo.ZoneInfo("America/New_York")` 自动处理 DST。避免 pytz 的 `localize` 陷阱。

### D3: 初筛条件 — RSI < 35 + IVR < 30

**选择**: 双重过滤，只有同时满足才进入深潜

- RSI < 35: 超卖区 → 长线买入窗口
- IVR < 30: 低波环境 → 远期期权便宜 (Vega 成本低)
- 单独满足一个不触发 → 减少 70%+ 的期权链 API 调用

### D4: API 节流策略 — 随机延迟

**选择**: 每次请求间 `random.uniform(1.0, 3.0)` 秒延迟

yfinance 无官方限流文档，但经验值 > 2000 req/h 触发 429。20 只标的 × 3s ≈ 60s/轮，安全余量大。

### D5: 微信推送集成 — Server酱 vs PushPlus

**选择**: Server酱 (sct.ftqq.com) 优先, PushPlus 备选

Server酱: 单 HTTP POST + SendKey，免费版每天 5 条。PushPlus: 不限量但需注册 token。两者均为 Webhook，实现代码几乎一致，配置化切换。

### D6: 冷却池存储 — 内存 dict vs Redis

**选择**: 进程内 `dict[str, float]` (ticker → timestamp)

进程重启时冷却池清零可接受 (不是交易执行，只是通知去重)。省去 Redis 序列化。

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| yfinance 429 限流 | 整轮扫描失败 | D4 随机延迟 + 重试 3 次 + 指数退避 |
| Server酱每日 5 条限制 | 多标的同时触发时丢信号 | 优先推最高 confidence 标的，附加 Email 通道兜底 |
| 进程 OOM / 死锁 | 扫描停止 | PM2 `max_memory_restart` + 每日心跳检测 |
| DST 切换日 (3月/11月) | 扫描时间窗偏移 1 小时 | `zoneinfo` 自动处理, 无需手动调整 |
