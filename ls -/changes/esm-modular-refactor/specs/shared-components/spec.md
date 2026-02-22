# Shared Components Spec

## Requirement: R1 — Toast Component
`showToast(message, type='info')` — 全局消息提示。
类型: `'success'` (绿), `'error'` (红), `'warning'` (橙), `'info'` (蓝)。
自动 3s 后消失，支持手动关闭。
复用现有 `.toast-container` DOM 结构。

## Requirement: R2 — Modal Component
`openModal(id)` / `closeModal(id)` — 通用暗黑玻璃态弹窗。
点击 overlay 或 Escape 键关闭。
支持回调: `openModal(id, { onClose: () => {} })`。

## Requirement: R3 — Format Utilities
- `formatMoney(num)` → `$1,234.56`
- `formatPercentage(num)` → `+12.34%` (带正号)
- `formatDate(dateStr)` → `2026-02-21`
- `formatDelta(num)` → `Δ 0.35` (保留 3 位)
导出为纯函数，不依赖 DOM 或 state。

## Requirement: R4 — Black-Scholes Engine
将 `BlackScholesEngine` 对象提取到 `js/utils/bs-engine.js`。
包含: `normalCDF`, `bsPrice`, `bsDelta`, `bsGamma`, `bsTheta`, `bsVega`。
纯数学计算，零 DOM 依赖。

## Requirement: R5 — Event Delegation Pattern
所有视图使用事件委托: `container.addEventListener('click', handler)`。
handler 内用 `e.target.closest('[data-action]')` 匹配目标。
每个 view 的 `init()` 只绑定一次，不因 re-render 重复绑定。
