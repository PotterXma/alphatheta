## Context

AlphaTheta 前端已完成 v7.0 SPA + CRO v2 风控 + 择时决策树，全部跑在客户端 Mock 数据上。后端 v2 需要将这些业务逻辑提升为生产级服务端实现，对接 IBKR 券商 API，并具备华尔街级的容灾、幂等性、可观测性和合规审计能力。

## Goals / Non-Goals

**Goals:**
- 6 大服务模块独立内聚，通过 DI 组合 (FastAPI Depends)
- 多层存储：PostgreSQL (订单/持仓/审计) + TimescaleDB (Tick/Greeks 时序) + Redis (行情/熔断/会话)
- 订单状态机 + 幂等 Idempotency-Key + 独立对账守护进程
- 交易日历中间件 (NTP + 美股节假日 + 提前闭盘)
- Paper/Live 环境物理隔离 (独立数据库 schema 或 prefix)
- OpenTelemetry 全链路追踪 + Prometheus Metrics
- K8s 友好：健康探针、平滑上下线、Replay Engine 用于 CI/CD

**Non-Goals:**
- 不修改现有前端代码（前端对接属后续 change）
- 不实现 HFT 低延迟（目标 < 500ms 端到端）
- 不做多账户管理（单账户模式）

## Decisions

### 1. 项目结构：分层 + 领域驱动

```
backend/
├── pyproject.toml
├── Dockerfile / docker-compose.yml
├── k8s/                         # K8s manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── alembic/                     # DB migrations
├── app/
│   ├── main.py                  # FastAPI app + lifespan
│   ├── config.py                # Pydantic Settings (Paper/Live 隔离)
│   ├── dependencies.py          # DI container
│   ├── models/                  # SQLAlchemy ORM
│   │   ├── order.py             # 订单状态机
│   │   ├── position.py          # 持仓快照
│   │   ├── audit_log.py         # 不可篡改审计
│   │   ├── kill_switch.py       # 熔断器
│   │   ├── api_key.py           # 加密存储
│   │   └── tick.py              # TimescaleDB hypertable
│   ├── schemas/                 # Pydantic DTOs
│   ├── services/                # 业务逻辑
│   │   ├── market_calendar.py   # 行情 + 日历
│   │   ├── risk_engine.py       # 风控引擎
│   │   ├── strategy_timing.py   # 策略择时
│   │   ├── order_manager.py     # OMS 状态机
│   │   ├── reconciliation.py    # 独立对账守护
│   │   ├── admin.py             # 系统管理
│   │   └── reporting.py         # 高管报表
│   ├── adapters/                # 外部集成
│   │   ├── broker_base.py       # ABC
│   │   ├── ibkr.py              # IBKR TWS adapter
│   │   └── tradier.py           # Tradier REST adapter
│   ├── routers/                 # API 端点
│   ├── websocket/               # WS feed
│   ├── middleware/
│   │   ├── kill_switch.py
│   │   ├── idempotency.py       # Idempotency-Key 中间件
│   │   ├── calendar.py          # 交易日历中间件
│   │   └── rate_limit.py
│   └── telemetry/
│       ├── tracing.py           # OpenTelemetry setup
│       └── metrics.py           # Prometheus metrics
├── replay/                      # 数据回放引擎
│   ├── runner.py
│   └── fixtures/                # 历史极端行情 JSON
└── tests/
```

### 2. 多层存储分工

| 存储引擎 | 数据类型 | 一致性要求 |
|---------|---------|----------|
| PostgreSQL | orders, positions, audit_logs, kill_switch_state, api_keys | 强一致 (ACID) |
| TimescaleDB (PG 扩展) | tick_data, greeks_snapshots | 时序优化，自动分区 |
| Redis | market:tick:{ticker}, market:indicators, system:kill_switch, idempotency:{key} | 最终一致，TTL 管理 |

### 3. 订单状态机 + 幂等性

```
Draft ─submit()→ Pending ─broker_ack()→ Filled
                    │                      │
                    ├─broker_reject()→ Rejected
                    ├─broker_partial()→ PartialFill ─fill_remaining()→ Filled
                    └─cancel()→ Cancelled
```

所有 `submit()` 调用强制携带 `Idempotency-Key`（UUID v4），Redis 记录 `idempotency:{key}` (TTL 24h)，重复提交直接返回缓存的原始响应，不触发二次下单。

### 4. Paper / Live 环境隔离

通过 `config.py` 的 `ENV_MODE` 变量（`paper` / `live`）控制：
- 不同的 DB schema prefix: `paper_orders` vs `live_orders`
- 不同的 broker adapter: `PaperBrokerAdapter` (本地模拟) vs `IBKRAdapter`
- Kill Switch 状态独立：`system:kill_switch:paper` vs `system:kill_switch:live`
- API 响应头标记 `X-Env-Mode: paper|live`

### 5. 交易日历中间件

- 启动时加载美股交易日历 (`exchange_calendars` 库)
- 每个 API 请求经过 `CalendarMiddleware`：休市期间拒绝发单操作 (返回 409)
- 提前闭盘日 (如圣诞前夕 13:00 EST 收盘) 自动调整决策树 DTE 计算
- 内部 NTP 同步确保时钟精度 < 100ms

### 6. 可观测性栈

- **OpenTelemetry**: FastAPI 自动 instrument + 自定义 span (broker API call, risk evaluation)
- **TraceID**: 从 WebSocket 行情信号到券商确认，贯穿全链路
- **Prometheus**: `/metrics` 端点暴露 api_latency_seconds, risk_rejections_total, orders_submitted_total, reconciliation_mismatches_total 等
- **K8s**: Liveness (`/healthz`), Readiness (`/readyz`), Graceful Shutdown (SIGTERM → drain WS connections → flush pending writes)

## Risks / Trade-offs

- **[IBKR API 复杂度]** TWS API 使用有状态连接 → 首期先实现 Tradier REST adapter (无状态), IBKR 作为第二阶段
- **[TimescaleDB 运维成本]** 额外的扩展 → 使用 PG 14+ 原生分区作为降级方案，TimescaleDB 仅在需要高吞吐 tick 存储时启用
- **[Paper/Live 隔离开销]** 双 schema 增加迁移复杂度 → 使用 Alembic 多 schema 迁移策略，CI 验证两套 schema 同步
- **[对账守护进程]** 独立进程增加部署复杂度 → 在 K8s 中作为 sidecar 或 CronJob 部署
- **[OPRA 数据成本]** 全量期权链订阅成本极高 → 按需订阅 + 本地缓存 + 取消订阅空闲 ticker
