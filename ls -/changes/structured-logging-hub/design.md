## Context

AlphaTheta v2 后端使用 FastAPI + asyncio 扫描引擎。当前 `main.py` 用 `logging.getLogger("alphatheta")`，中间件链: RateLimit → KillSwitch → Calendar → Idempotency → Router。无结构化日志、无 Trace ID、无脱敏。

## Goals / Non-Goals

**Goals:**
- 统一日志入口: 所有模块 `from app.logging.logger_setup import logger`
- Console 人类可读 (颜色区分 INFO/WARN/ERROR) + File JSON (机器可读)
- 每日轮转 + 30天保留 + zip 压缩
- FastAPI Trace ID 中间件 (UUID, contextvars, `X-Trace-ID` header)
- 金融级脱敏: password/secret/token/api_key/Authorization → `***[MASKED]***`

**Non-Goals:**
- 替换现有所有模块的 `logging.getLogger()` (后续逐步迁移)
- 日志收集代理部署 (ELK/Loki)
- OpenTelemetry Span 集成 (已有 `tracing.py`)

## Decisions

### D1: loguru 而非 structlog

loguru 提供 `add()` sink 配置、内置轮转/压缩、`contextvars` 原生支持(`bind()`)，且 API 极简。structlog 需手动组装 pipeline。
新增 `loguru` 到 `requirements.txt`。

### D2: 日志目录 — `logs/`

```
logs/
  alphatheta.log          # 当前日志 (JSON)
  alphatheta.2026-02-22.log.zip  # 轮转压缩
```

Docker 部署时 volume mount `/app/logs`。

### D3: TraceIdMiddleware 位置 — 最外层

插入在所有其他中间件之前（RateLimit 之前），确保所有日志都带 Trace ID：
```
TraceId → RateLimit → KillSwitch → Calendar → Idempotency → Router
```

### D4: 脱敏位置 — loguru patcher

使用 loguru 的 `logger.patch()` 机制，在 record 写入任何 sink 之前执行脱敏。
遍历 `record["extra"]` 字典 + 正则扫描 `record["message"]`。

### D5: 标准 logging 桥接

使用 loguru 的 `InterceptHandler` 将标准 `logging` 模块的输出重定向到 loguru，确保现有 `logging.getLogger()` 调用自动受益于 JSON 输出和脱敏。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| loguru 不是标准库 | 已广泛使用于 Python 生态，API 稳定 |
| 脱敏正则可能漏网 | 敏感字段白名单 + 正则双重检查 |
| 日志文件占磁盘 | 轮转 + 30天保留 + zip 压缩 |
| contextvars 在非 asyncio 上下文中丢失 | Daemon 进程手动 `bind(trace_id=...)` |
