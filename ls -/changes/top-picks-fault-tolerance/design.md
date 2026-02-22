# Design Decisions

## D1: Per-Ticker Timeout via asyncio.wait_for
- 每个 `_get_earnings_date` 和 `_get_premium_yield` 调用包裹 `asyncio.wait_for(timeout=10s)`
- 超时产生 `asyncio.TimeoutError` → 捕获后返回 `None` → `asyncio.gather` 继续
- 理由: 防止单个 yfinance 响应挂住整个事件循环

## D2: Global Exception Shield
- 整个 `get_top_picks()` handler 包在 `try/except Exception` 中
- 任何未预期异常 → HTTP 200 + `{"picks": [], "message": "服务异常: ..."}`
- 理由: FastAPI 默认会将未捕获异常转为 500，导致前端 JSON 解析失败

## D3: Client-Side AbortController
- 前端使用 `AbortController` 设置 15s 超时（后端 10s + 5s 缓冲）
- `AbortError` → 专门的超时提示 UI
- `finally` 块保证 `clearTimeout` 释放
- 理由: 双重保险，即使后端超时机制失效，前端也不会无限等待

## D4: Error UI with Retry
- 异常状态: 红色 ⚠️ 警告 + 🔄 重试按钮（调 `TopPicksManager.fetchTopPicks()`）
- 空结果状态: 📭 + 服务端消息 + 已扫描数量
- 理由: 用户需要明确知道发生了什么，并能一键重试
