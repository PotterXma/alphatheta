# Top Picks 容错强化

## Problem
"Top 3 智能推荐"卡片陷入无限 Loading 状态 ("⏳ 正在扫描票池...")。
根因: `yfinance` 第三方 API 超时/异常导致后端 500，前端缺少 Promise 异常捕获和 HTTP 状态码校验。

## Solution
重构推荐模块前后端代码，覆盖所有异常分支，确保 UI 绝对不会卡死在 Loading 状态。

## Capabilities

### CAP-1: 后端单标的超时隔离
- 每个 `yfinance` 调用包裹 `asyncio.wait_for(timeout=10s)`
- 超时/异常 → 安全跳过该标的，不影响其他
- 全局 `try/except` 兜底 → 绝不返回 500

### CAP-2: 前端防御性 Fetch + 优雅降级
- `AbortController` + 15s 客户端超时
- `!response.ok` HTTP 状态墙
- `finally` 保证清理
- 错误 UI: ⚠️ 红色警告 + 🔄 重试按钮
- 空结果 UI: 📭 优雅提示
