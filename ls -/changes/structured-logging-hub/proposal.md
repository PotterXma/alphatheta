## Why

后端全系统 ~50 个 Python 文件使用原生 `logging.getLogger()` 并含有散落的 `print()`。日志输出为纯文本、无结构化 JSON、无 Trace ID 流转、无机密脱敏——完全不符合金融级 SaaS 的可观测性要求。出问题时无法快速关联请求链路，且敏感数据（API Key、Token）可能泄露到日志文件。

## What Changes

- **[NEW] `logger_setup.py`**: 基于 loguru 的日志中枢 — Console 人类可读彩色输出 + File JSON 轮转输出 + 脱敏钩子
- **[NEW] `TraceIdMiddleware`**: FastAPI 中间件，用 `contextvars` 为每个请求注入 UUID Trace ID，响应 header `X-Trace-ID`
- **[NEW] 脱敏过滤器**: 正则 + 字典遍历拦截器，将 `password/secret/token/api_key/Authorization` 值替换为 `***[MASKED]***`
- **[MODIFY] `main.py`**: 替换 `logging.getLogger()` → loguru `logger`，注册 TraceIdMiddleware

## Capabilities

### New Capabilities
- `structured-logging`: loguru 日志中枢 + JSON 文件输出 + 轮转 + Trace ID + 脱敏

### Modified Capabilities
_(无已有 spec 需要修改)_

## Impact

- **新增文件**: `backend/app/logging/logger_setup.py`, `backend/app/middleware/trace_id.py`
- **修改文件**: `backend/app/main.py` (import + middleware 注册)
- **依赖**: `loguru` (需添加到 `requirements.txt`)
- **迁移**: 后续可逐步将各模块的 `logging.getLogger()` 替换为 `from app.logging.logger_setup import logger`
