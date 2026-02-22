## Why

将 Pydantic DTOs 从简单 BaseModel 升级为生产级严格校验，利用 Pydantic v2 特性（field_validator, model_validator, StrEnum, Field 约束）。日历中间件从简单时间比较升级为 timezone-aware、支持提前闭盘的完整实现。

## What Changes

- **Rewrite** `schemas/order.py`: 新增 UUID idempotency_key 必填, OCC 合约正则, StrEnum, model_validator
- **Rewrite** `schemas/risk.py`: TradeProposal 嵌套 OrderCreate, 严格 Field 约束, rejection_rule 字段
- **Rewrite** `schemas/market.py`: DataQuality 枚举, CalendarStatus 含 holiday_name 和 is_early_close  
- **Rewrite** `middleware/calendar.py`: timezone-aware UTC 比较, 提前闭盘检测, 409+CalendarStatus JSON

## Capabilities

### Modified Capabilities
- `market-calendar-service`: CalendarStatus 增加 holiday_name/is_early_close, 中间件升级
- `order-lifecycle-manager`: OrderCreate 增加 idempotency_key 必填和 OCC 合约校验
- `risk-engine-backend`: TradeProposal 引用 OrderCreate，增加 rejection_rule 追踪

## Impact

- `app/schemas/order.py` — 全量重写
- `app/schemas/risk.py` — 全量重写
- `app/schemas/market.py` — 全量重写
- `app/middleware/calendar.py` — 全量重写
