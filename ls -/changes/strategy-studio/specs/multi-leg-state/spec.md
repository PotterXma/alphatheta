## multi-leg-state

状态基石: 管理任意数量期权/正股腿的 CRUD、双向绑定渲染、以及实时 Net Premium 计算。

### Requirements

- **R1 — Leg 数据结构**: 每条 Leg 必须包含: `id` (UUID), `type` ('option'|'stock'), `right` ('call'|'put'|null), `action` ('buy'|'sell'), `expiration` (ISO date string|null), `strike` (number), `quantity` (number ≥ 0), `price` (number ≥ 0), `multiplier` (100 for options, 1 for stock)

- **R2 — CRUD 操作**: 提供 `addLeg()`, `removeLeg(id)`, `updateLeg(id, patch)`, `clearAllLegs()`, `loadTemplate(templateLegs)` 方法。每次操作后触发 `renderLegs()` + `recalcPayoff()` 级联刷新。

- **R3 — 双向绑定**: UI 控件变更(买/卖切换, Call/Put/Stock切换, 数量输入等)必须先更新 `currentLegs` 数组，再触发全量重新渲染。严禁从 DOM 读取状态。

- **R4 — Net Premium 实时计算**: 监听任何 Leg 变动，实时遍历 `currentLegs` 计算:
  ```
  Net = Σ(sell legs: price × qty × multiplier) - Σ(buy legs: price × qty × multiplier)
  ```
  Net > 0 显示 "Net Credit" (绿色), Net < 0 显示 "Net Debit" (红色)。

- **R5 — 策略模板覆写**: 选择模板时，使用 `snapToStrike()` 将模板中的 `strikeStep` 相对偏移转换为绝对行权价，并根据 `dteOffset` 计算绝对到期日，完全覆写 `currentLegs` 并触发重新渲染。
