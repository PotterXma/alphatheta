# Fault Tolerance Spec

## Requirement: R1 — Per-Ticker Timeout
`_get_earnings_date` 和 `_get_premium_yield` 必须使用 `asyncio.wait_for(timeout=10s)` 包裹。
超时时返回 `None`，打印 WARNING 日志，不影响其他标的。

## Requirement: R2 — Global Exception Shield
`get_top_picks()` 整体包裹 `try/except Exception`。
任何未捕获异常返回 HTTP 200 + `{"picks": [], "message": "..."}` 而非 500。

## Requirement: R3 — Client AbortController
前端 `fetchTopPicks()` 使用 `AbortController` 设置 15s 超时。
`AbortError` 触发专用超时提示 UI。

## Requirement: R4 — HTTP Status Wall
前端在 `fetch()` 后必须检查 `!response.ok`，不满足时 `throw`，防止解析 HTML 报错。

## Requirement: R5 — Guaranteed UI Reset
无论成功/失败/超时，`finally` 块必须清理 timer。
`catch` 块必须渲染错误 UI（红色警告 + 重试按钮），保证 Loading 状态被替换。

## Requirement: R6 — Empty State
后端返回 `[]` 时，前端渲染 📭 优雅提示："暂无符合...推荐标的，建议观望。"
