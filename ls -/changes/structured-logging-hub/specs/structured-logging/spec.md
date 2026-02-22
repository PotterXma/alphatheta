## ADDED Requirements

### Requirement: Structured Log Output
系统 SHALL 通过 loguru 提供双 sink 日志输出:
- Console: 人类可读格式，带颜色区分 (INFO 绿色, WARN 黄色, ERROR 红色) 和 `[trace_id]` 前缀
- File: 纯 JSON 格式，每行一个 JSON 对象

#### Scenario: Console output includes trace_id
- **WHEN** 任何日志消息被记录
- **THEN** Console 输出 MUST 包含 `[{trace_id}]` 字段

#### Scenario: File output is valid JSON
- **WHEN** 日志写入文件
- **THEN** 每行 MUST 为合法 JSON，包含 `timestamp`, `level`, `message`, `trace_id`, `module` 字段

---

### Requirement: Log Rotation and Retention
系统 SHALL 配置日志文件轮转策略: 每日午夜轮转 (`rotation="00:00"`)，保留 30 天 (`retention="30 days"`)，压缩为 zip (`compression="zip"`)。

#### Scenario: Daily rotation creates new file
- **WHEN** 系统时钟跨越午夜 00:00
- **THEN** 当前日志文件 MUST 被轮转并压缩为 `.zip`

#### Scenario: Old logs are purged
- **WHEN** 日志文件超过 30 天
- **THEN** 该文件 MUST 被自动删除

---

### Requirement: Trace ID Middleware
FastAPI 应用 MUST 注册 `TraceIdMiddleware`，为每个 HTTP 请求生成唯一 UUID Trace ID。

#### Scenario: Request gets trace_id
- **WHEN** 任何 HTTP 请求到达 FastAPI
- **THEN** 系统 MUST 生成 UUID 并通过 `contextvars` 绑定到当前协程上下文

#### Scenario: Response includes X-Trace-ID header
- **WHEN** HTTP 响应返回给客户端
- **THEN** 响应 Headers MUST 包含 `X-Trace-ID: <uuid>`

#### Scenario: All logs within request carry trace_id
- **WHEN** 请求处理过程中产生任何日志
- **THEN** 日志记录 MUST 包含该请求的 `trace_id`

---

### Requirement: Financial Data Sanitization
系统 SHALL 在日志写入前拦截并脱敏所有敏感数据。

#### Scenario: Sensitive extras are masked
- **WHEN** 日志的 `extra` 字典中包含键名匹配 `password|secret|token|api_key|authorization` (不区分大小写) 的条目
- **THEN** 该值 MUST 被替换为 `***[MASKED]***`

#### Scenario: Sensitive patterns in message are masked
- **WHEN** 日志 message 字符串中包含形如 `Bearer <token>` 或 `api_key=<value>` 的模式
- **THEN** 敏感部分 MUST 被替换为 `***[MASKED]***`

---

### Requirement: Standard Logging Bridge
系统 SHALL 将 Python 标准 `logging` 模块的输出重定向到 loguru，使现有 `logging.getLogger()` 调用自动受益于 JSON 输出和脱敏。

#### Scenario: Existing logging calls are captured
- **WHEN** 任何模块通过 `logging.getLogger().info(...)` 输出日志
- **THEN** 输出 MUST 经过 loguru 的 sink 处理（包括 JSON 格式化和脱敏）
