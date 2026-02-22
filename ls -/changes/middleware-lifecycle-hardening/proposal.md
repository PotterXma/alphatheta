## Why

验证报告发现 `backend-trading-engine` 的中间件和生命周期存在 7 个 WARNING 级缺陷：middleware 未注册、metrics/WS 路由缺失、幂等实现不健壮、kill switch 无本地缓存。需要生产级重写。

## What Changes

- **Rewrite** `app/middleware/idempotency.py`: SETNX 原子两阶段写入、UUID 格式校验、409 并发冲突响应、Redis 降级放行
- **Rewrite** `app/middleware/kill_switch.py`: 1 秒本地缓存、豁免管理路径、X-Env-Mode Header 感知、503+Retry-After
- **Rewrite** `app/main.py`: 完整 lifespan (日历/OTel/信号处理/30s 超时排空)、5 层 middleware 注册、metrics 和 WS 路由接入、真实 /readyz 健康检查

## Capabilities

### Modified Capabilities
- `observability-infra`: /readyz 从假响应改为真实 PG+Redis ping
- `risk-engine-backend`: kill switch 中间件从仅拦截 /orders 改为拦截所有突变操作

## Impact

- `app/middleware/idempotency.py` — 全量重写
- `app/middleware/kill_switch.py` — 全量重写
- `app/main.py` — 全量重写
- 修复验证报告中 W4-W9 全部 WARNING
