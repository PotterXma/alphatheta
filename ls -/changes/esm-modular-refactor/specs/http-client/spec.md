# HTTP Client Spec

## Requirement: R1 — Base URL Auto-Prefix
所有请求路径自动拼接 `window.location.origin`。
`get('/api/v1/foo')` → `fetch('http://host:port/api/v1/foo')`。

## Requirement: R2 — AbortController Timeout
每个请求创建 `AbortController`，默认 15s 超时。
超时触发 `controller.abort()` → `AbortError`。
`finally` 块保证 `clearTimeout`，无泄漏。

## Requirement: R3 — Response Interceptor
`!response.ok` → throw `ApiError { status, statusText, url }`。
`response.json()` 解析失败 → throw `ApiError { message: 'Invalid JSON' }`。
4xx/5xx 在消费者的 `catch` 中统一处理。

## Requirement: R4 — Convenience Methods
导出 `get(path, opts)`, `post(path, data, opts)`, `del(path, opts)`。
`post` 自动设置 `Content-Type: application/json` + `JSON.stringify(data)`。

## Requirement: R5 — ApiError Class
自定义 `class ApiError extends Error`。
包含 `status`, `statusText`, `url` 属性，方便上层按状态码分支处理。
