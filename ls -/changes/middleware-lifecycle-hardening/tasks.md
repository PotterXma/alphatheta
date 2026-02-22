## 1. Middleware Rewrite

- [x] 1.1 `idempotency.py`: SETNX 原子抢占 + "processing" 占位 + 300s 死锁防护
- [x] 1.2 `idempotency.py`: UUID v4 格式正则校验
- [x] 1.3 `idempotency.py`: 409 Conflict 响应 (同 Key 请求并发)
- [x] 1.4 `idempotency.py`: Redis 不可用时安全降级放行
- [x] 1.5 `kill_switch.py`: 1 秒 monotonic 本地缓存减少 Redis 压力
- [x] 1.6 `kill_switch.py`: 豁免路径集合 (/healthz, /admin/kill-switch, /docs)
- [x] 1.7 `kill_switch.py`: X-Env-Mode Header 优先级高于 config
- [x] 1.8 `kill_switch.py`: Redis 值支持 "1:reason" 格式

## 2. main.py Lifecycle

- [x] 2.1 exchange_calendars NYSE 加载到全局缓存
- [x] 2.2 OpenTelemetry SDK 初始化 (non-fatal on failure)
- [x] 2.3 SIGTERM/SIGINT 信号处理 → _shutting_down 标志
- [x] 2.4 30 秒超时等待 in-flight 事务
- [x] 2.5 关闭 WebSocket 连接 (code=1001)
- [x] 2.6 Redis 连接池关闭
- [x] 2.7 OTel spans force_flush

## 3. main.py Wiring

- [x] 3.1 注册 5 层 Middleware (CORS → RateLimit → KillSwitch → Calendar → Idempotency)
- [x] 3.2 注册 metrics_router (/metrics 端点)
- [x] 3.3 注册 ws_router (WebSocket feed)
- [x] 3.4 /healthz 在关闭期间返回 503
- [x] 3.5 /readyz 真实检查 PG + Redis 连接
