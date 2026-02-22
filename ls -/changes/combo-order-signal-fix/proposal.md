## Why

信号与执行 (Signal & Execution) 模块存在三个问题：

1. **前端 Mock 数据断链**: VIX 徽章显示 `undefined`，权利金金额与限价不一致，风控文案不符合 Margin 扣减逻辑
2. **无净成本展示**: Buy-Write 策略的净支出 (Net Debit) 没有可视化，用户无法直观判断资金影响
3. **组合单拆分风险**: 当前 Buy-Write 分为两个独立订单发送,存在"滑腿风险 (Legging Risk)" — 第一腿成交后市场剧变导致第二腿成本失控

## What Changes

- **前端**: 修复 `renderSignal()` 中 VIX/权利金/文案的 Mock 数据绑定，新增 Net Debit 高亮展示
- **后端 DTO**: `schemas/order.py` 新增 `ComboLeg` 模型 + `is_combo`/`combo_legs`/`net_price` 字段
- **券商适配器**: `broker_base.py` 新增 `submit_combo_order()` 抽象方法，`tradier.py` 实现 multileg 组合单

## Capabilities

### New Capabilities
- `combo-order`: 原子组合单 (Buy-Write) 的 DTO 定义、券商适配器实现、前端 Net Debit 展示

### Modified Capabilities
_(无已有 spec 需修改)_

## Impact

- `app.js` — renderSignal() 函数 + MOCK_DATA.currentSignal
- `backend/app/schemas/order.py` — OrderCreate 扩展
- `backend/app/adapters/broker_base.py` — 新增抽象方法
- `backend/app/adapters/tradier.py` — multileg 实现
