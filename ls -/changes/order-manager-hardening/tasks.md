## 1. OrderManagerService Core

- [x] 1.1 `submit_order(order_create_dto)` — Draft → Pending → Filled/Rejected/Pending
- [x] 1.2 幂等: `_find_by_idempotency_key()` 去重
- [x] 1.3 券商通信失败 → REJECTED + 错误原因记录
- [x] 1.4 同步成交 → `_apply_fill()` 原子更新 order + position

## 2. Async Execution Report

- [x] 2.1 `handle_broker_execution_report(order_id, ExecutionReport)`
- [x] 2.2 `session.begin_nested()` SAVEPOINT 嵌套事务
- [x] 2.3 FSM 终态保护 (Filled/Rejected/Cancelled → 任何 = InvalidStateTransition)
- [x] 2.4 PartialFill 中间态支持
- [x] 2.5 `_map_report_to_status()` — 券商状态 → 内部 FSM (含美式拼写兼容)

## 3. Position Atomic Update

- [x] 3.1 `_apply_fill()` — BUY: 加仓 + 加权平均成本
- [x] 3.2 `_apply_fill()` — SELL: 减仓 (avg_cost 不变)
- [x] 3.3 首次建仓 → INSERT Position 新记录
- [x] 3.4 方向判断: action_type.lower() 包含 "sell" → 卖出

## 4. Cancel + Query

- [x] 4.1 `cancel_order()` — 尽力通知券商 + 本地 FSM
- [x] 4.2 `get_order()`, `list_orders()`, `list_positions()`
- [x] 4.3 `calculate_roll()` — 展期计算 (Roll Up/Down/Out)
