## Capability: roll-combo-order
展期组合单 API + 限价预览 Modal + TransactionLedger 原子写入

### Requirement: ROLL-01 — 展期 Modal UI
- 暗黑玻璃态弹窗，从"全程跟踪"页的"展期"按钮触发
- 展示字段:
  - 旧仓: ticker, strike, expiration, 当前 bid (预估平仓成本)
  - 新仓: 新 expiration (dateInput), 新 strike (numberInput), 当前 ask (预估开仓收入)
  - **Net Credit / Net Debit**: 高亮显示 (绿色 credit / 红色 debit)
- 限价微调输入框 (`Net Limit Price`), 不允许市价单
- 确认按钮 + 取消按钮

### Requirement: ROLL-02 — `POST /api/v1/orders/roll_combo` API
- **Request Body**:
  ```json
  {
    "old_order_id": "uuid",
    "new_strike": 460.0,
    "new_expiration": "2026-04-18",
    "net_limit_price": 0.85,
    "quantity": 1
  }
  ```
- **Business Logic**:
  1. 验证 old_order_id 存在且状态为 FILLED 或 PARTIAL_FILL
  2. 在同一数据库事务中:
     - 标记旧 Order → CANCELLED (Buy to Close)
     - 创建新 Order (Sell to Open, status=PENDING)
     - 写入 TransactionLedger 两条记录 (roll_close + roll_open)
  3. 事务失败 → 全量回滚，返回 500
- **Response**: 新 Order 详情 + ledger 条目

### Requirement: ROLL-03 — TransactionLedger 模型
- 表名: `transaction_ledger`
- 字段: id, order_id, ticker, leg_type, quantity, price, net_amount, created_at
- `leg_type` 枚举: `open`, `close`, `roll_close`, `roll_open`
- `net_amount` = quantity × price × 100 (期权合约乘数)

#### Scenario: 正常展期 (Net Credit)
- 旧仓 AAPL 450P exp 3/14, bid=$1.20
- 新仓 AAPL 450P exp 4/18, ask=$3.50
- Net Credit = $3.50 - $1.20 = $2.30
- Modal 高亮绿色显示 "Net Credit: $2.30"
- 确认后: 旧 Order → CANCELLED, 新 Order → PENDING, Ledger 写入两条

#### Scenario: 展期失败回滚
- 旧 Order 不存在或状态不合法
- API 返回 400 + 错误消息
- 数据库无任何修改
