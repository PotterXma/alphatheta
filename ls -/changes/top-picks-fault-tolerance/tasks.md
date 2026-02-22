## 后端容错

- [x] 1.1 `_get_earnings_date`: 包裹 `asyncio.wait_for(timeout=10s)` + 捕获 `TimeoutError`
- [x] 1.2 `_get_premium_yield`: 包裹 `asyncio.wait_for(timeout=10s)` + 捕获 `TimeoutError`
- [x] 1.3 `get_top_picks()`: 全局 `try/except Exception` 兜底 → HTTP 200 + `{"picks": []}`
- [x] 1.4 超时/异常时打印 `[TopPicks] ⏱ TIMEOUT` WARNING 日志
- [x] 1.5 空 Watchlist → 返回 `{"picks": [], "message": "票池为空"}`

## 前端防御性 Fetch

- [x] 2.1 `AbortController` + 15s 客户端超时
- [x] 2.2 `!response.ok` HTTP 状态墙 → `throw new Error`
- [x] 2.3 `catch` 块: 区分 `AbortError` (超时) vs 通用异常
- [x] 2.4 错误 UI: ⚠️ 红色警告 + `onclick` 重试按钮
- [x] 2.5 空结果 UI: 📭 优雅提示 + 已扫描标的数
- [x] 2.6 `finally` 块: `clearTimeout(timeoutId)` 保证释放

## 验证

- [x] V1 Docker rebuild 无 import 错误
- [x] V2 API 启动 healthy
