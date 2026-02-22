## 1. Order Schema (`schemas/order.py`)

- [x] 1.1 `idempotency_key: uuid.UUID` 作为必填字段 (前端生成)
- [x] 1.2 `ticker` — 自动大写 + strip, min_length=1, max_length=10
- [x] 1.3 `contract_symbol` — OCC 正则 `^[A-Z]{1,6}\d{6}[CP]\d{8}$`
- [x] 1.4 `OrderAction(StrEnum)` — BUY/SELL 二选一
- [x] 1.5 `OrderType(StrEnum)` — limit/market/limit_price_chaser
- [x] 1.6 `quantity` — gt=0, le=100 约束
- [x] 1.7 `expiration` — YYYY-MM-DD pattern 校验
- [x] 1.8 `model_validator` — 期权订单要求 strike + expiration 同时提供

## 2. Risk Schema (`schemas/risk.py`)

- [x] 2.1 `TradeProposal.order: OrderCreate` — 嵌套引用，避免字段重复
- [x] 2.2 `delta` — ge=-1.0, le=1.0 约束
- [x] 2.3 `projected_margin_util` — ge=0, le=100 约束
- [x] 2.4 `est_tax_drag` — 默认 0.30, ge=0, le=1.0
- [x] 2.5 `RiskAssessment.rejection_rule` — 新增, 关联 Prometheus 指标打点

## 3. Market Schema (`schemas/market.py`)

- [x] 3.1 `DataQuality(StrEnum)` — realtime/delayed/stale/insufficient 四级
- [x] 3.2 `vix` — ge=0, le=100, description 关联 VIX Override 阈值
- [x] 3.3 `rsi_14` — ge=0, le=100, description 关联 Scene A/B 判断
- [x] 3.4 `available_cash` — 新增字段, ge=0
- [x] 3.5 `CalendarStatus` — next_open/next_close 使用 timezone-aware datetime
- [x] 3.6 `CalendarStatus.holiday_name` — 新增, 休市原因

## 4. Calendar Middleware (`middleware/calendar.py`)

- [x] 4.1 模块级 `exchange_calendars.get_calendar("XNYS")` 初始化
- [x] 4.2 区分 GET (放行) vs POST/PUT/DELETE (检查日历)
- [x] 4.3 豁免 admin / healthz / WS 路径
- [x] 4.4 UTC 时区统一比较 (避免 DST 问题)
- [x] 4.5 提前闭盘检测 (`close.hour < 19` UTC 启发式)
- [x] 4.6 409 Conflict + CalendarStatus JSON 响应体
- [x] 4.7 盘前 vs 盘后分支 — 正确计算 next_open
- [x] 4.8 节假日名称推断 (固定日期 + 工作日非交易日检测)
