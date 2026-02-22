## ADDED Requirements

### Requirement: 零报价拦截
系统 SHALL 在 Bid ≤ 0 或 Ask ≤ 0 时立即拒绝该合约，抛出流动性枯竭错误。

#### Scenario: Bid 为零
- **WHEN** 合约 Bid = 0, Ask = 15.00
- **THEN** 系统抛出错误 `"远期期权流动性严重枯竭，Bid/Ask 为零，无法安全成交。"`

### Requirement: 绝对价差上限 $3.00
系统 SHALL 在 Ask - Bid > $3.00 时拒绝该合约。

#### Scenario: 绝对价差超限
- **WHEN** 合约 Bid = 12.00, Ask = 16.00 (价差 $4.00)
- **THEN** 系统抛出错误，包含实际价差金额

#### Scenario: 绝对价差在限内
- **WHEN** 合约 Bid = 12.00, Ask = 14.50 (价差 $2.50)
- **THEN** 系统通过流动性校验

### Requirement: 相对价差上限 15%
系统 SHALL 在 (Ask - Bid) / Ask > 15% 时拒绝该合约。分母使用 Ask 而非 Bid，确保分母不为零或极小值。

#### Scenario: 相对价差超限
- **WHEN** 合约 Bid = 1.00, Ask = 1.50 (相对价差 33%)
- **THEN** 系统抛出错误，包含实际相对价差百分比

#### Scenario: 相对价差在限内
- **WHEN** 合约 Bid = 12.00, Ask = 13.50 (相对价差 11.1%)
- **THEN** 系统通过流动性校验

### Requirement: 双重门控优先级
系统 SHALL 按以下优先级依次校验: 零报价 → 绝对价差 → 相对价差。首个失败即抛出对应错误。

#### Scenario: 同时违反绝对和相对
- **WHEN** 合约 Bid = 1.00, Ask = 5.00 (绝对 $4.00 超限, 相对 80% 超限)
- **THEN** 系统抛出绝对价差超限的错误 (优先)
