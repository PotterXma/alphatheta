## 1. 依赖安装

- [x] 1.1 将 `loguru` 添加到 `backend/requirements.txt`

## 2. 核心: logger_setup.py

- [x] 2.1 创建 `backend/app/logging/__init__.py` (空文件)
- [x] 2.2 创建 `backend/app/logging/logger_setup.py` — loguru 配置中枢
- [x] 2.3 实现 Console sink: 人类可读彩色格式，包含 `[{extra[trace_id]}]`
- [x] 2.4 实现 File sink: JSON 格式写入 `logs/alphatheta.log`，轮转 `00:00` / 保留 `30 days` / 压缩 `zip`
- [x] 2.5 实现 `InterceptHandler` — 标准 logging → loguru 桥接
- [x] 2.6 实现 `sanitize_record()` patcher — 脱敏 `extra` 字典和 `message` 中的敏感数据
- [x] 2.7 暴露 `setup_logging()` 初始化函数 + `logger` 实例

## 3. Trace ID 中间件

- [x] 3.1 创建 `backend/app/middleware/trace_id.py` — `TraceIdMiddleware`
- [x] 3.2 实现 `contextvars.ContextVar("trace_id")` + UUID 生成
- [x] 3.3 实现响应 header 注入 `X-Trace-ID`
- [x] 3.4 使用 loguru `bind(trace_id=...)` 绑定到当前请求上下文

## 4. 集成到 main.py

- [x] 4.1 在 `main.py` 的 lifespan startup 中调用 `setup_logging()`
- [x] 4.2 注册 `TraceIdMiddleware` 为最外层中间件 (在 RateLimit 之前)
- [x] 4.3 替换 `logger = logging.getLogger("alphatheta")` 为 `from app.logging.logger_setup import logger`

## 5. 验证

- [x] 5.1 启动 API 容器，确认 Console 输出带颜色和 `[trace_id]`
- [x] 5.2 发送 HTTP 请求，确认响应 Headers 包含 `X-Trace-ID`
- [x] 5.3 检查 `logs/alphatheta.log` 文件内容为 JSON 格式
- [x] 5.4 测试脱敏: 故意日志一个含 `api_key` 的字典，确认值被替换为 `***[MASKED]***`
