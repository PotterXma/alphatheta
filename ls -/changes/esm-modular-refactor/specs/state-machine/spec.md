# State Machine Spec

## Requirement: R1 — Proxy-based Reactive State
使用 `new Proxy()` 拦截 state 对象的 `set` trap。
当任何 key 被修改时，自动触发该 key 的所有订阅者回调。

## Requirement: R2 — Subscribe/Unsubscribe API
`subscribe(key, callback)` 返回 `unsubscribe` 函数。
调用 `unsubscribe()` 后，该 callback 从订阅列表移除，防止视图销毁后的内存泄漏。

## Requirement: R3 — Safe Callback Dispatch
每个订阅回调在 `try/catch` 中执行。
单个 subscriber 抛出异常不影响其他 subscriber 收到通知。
异常打印 `console.error` 日志。

## Requirement: R4 — Initial State Schema
初始状态包含:
- `activeTicker: 'SPY'` — 全局联动标的
- `isAutoTrading: false` — 自动交易开关
- `lang: 'en'` — 语言 (en/zh)
- `activeTab: 'dashboard'` — 当前激活 Tab
- `theme: 'dark'` — 主题 (预留)

## Requirement: R5 — MOCK_DATA Compatibility
导出 `MOCK_DATA` 对象作为过渡层，供尚未迁移的视图引用。
最终所有视图从 API 获取数据后，MOCK_DATA 逐步删除。
