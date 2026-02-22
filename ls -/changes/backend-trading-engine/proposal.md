## Why

AlphaTheta 前端 SPA 运行在纯 Mock 数据上。要实现生产级自动化期权交易，需要一个 Python 后端作为**唯一事实数据源**和**执行引擎**，对接 IBKR 券商 API，管理订单全生命周期，并具备商业化级的容灾、可观测性和合规审计能力。系统需兼顾华尔街级的严谨性与低门槛创业的高性价比。

## What Changes

- 新建 Python FastAPI 后端项目 (`backend/`)，完整项目脚手架 + Docker + K8s 部署
- 5 大核心服务模块：行情日历、风控引擎、策略择时、订单生命周期、运维审计
- PostgreSQL 持久化（订单/持仓/审计） + TimescaleDB 扩展（Tick/Greeks 时序） + Redis 高频缓存
- **按需节流订阅** — OPRA 期权数据成本控制，429 限流熔断队列
- **交易日历中间件** — NTP 高精度时钟 + 美股节假日/提前闭盘处理
- **Paper / Live 环境隔离** — 物理或逻辑隔离，数据互不污染
- **幂等性设计** — 所有资金操作基于 Idempotency-Key 杜绝重复下单
- **订单状态机 + 独立对账守护进程** — 断网/Pod 驱逐后自动恢复
- **公司行动解析** — 分红/拆股动态调整 Strike Price
- **Pin Risk / DTE=0 强平逻辑** — 到期日自动平仓避免指派风险
- **OpenTelemetry 全链路追踪** + **Prometheus Metrics** 端点
- **Replay Engine** — CI/CD 中注入历史极端行情回放验证逻辑
- **高管汇报视角** — 自动生成风控拦截/展期对冲/规避损失的价值报表

## Capabilities

### New Capabilities
- `market-calendar-service`: 行情聚合 + 交易日历 — 按需节流订阅、Tick 缓存、RSI/SMA200/VIX 计算、NTP 时钟、美股节假日/提前闭盘、WebSocket 推送
- `risk-engine-backend`: 后端风控引擎 — 7 条 Kill Switch、Margin 校验、年化收益率、全局熔断器、Paper/Live 环境隔离
- `strategy-timing-service`: 策略择时 — 决策树 (Scene A-D)、沙盒推演、公司行动解析 (分红/拆股)、Pin Risk / DTE=0 到期日逻辑
- `order-lifecycle-manager`: 订单生命周期 — 状态机 (幂等)、展期计算、持仓跟踪、独立对账守护进程、券商适配器 (IBKR)
- `admin-audit-reporting`: 运维审计报表 — API Key 保险库、Kill Switch、不可篡改审计日志、高管价值报表、健康检查
- `observability-infra`: 可观测性基础设施 — OpenTelemetry 追踪、Prometheus Metrics、K8s 探针/平滑上下线、Replay Engine

### Modified Capabilities
- (none — 后端全新项目)

## Impact

- **新增**: `backend/` — 完整 FastAPI 项目 + Alembic 迁移 + Docker + K8s manifests
- **技术栈**: Python 3.12 + FastAPI + SQLAlchemy + TimescaleDB + Redis + Docker + K8s
- **外部依赖**: IBKR TWS API / Tradier REST API、NTP 服务、OPRA 数据源
- **安全**: Fernet 加密 API Key、CORS、Rate Limiting、环境隔离
- **前端**: Mock → API 替换属后续 change，本次不修改前端
