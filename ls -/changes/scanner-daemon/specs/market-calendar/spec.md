## ADDED Requirements

### Requirement: 交易时段判断
系统 SHALL 判断当前时间是否在美东 (America/New_York) 工作日 09:30-16:00 范围内。自动处理 EST/EDT (DST) 切换。

#### Scenario: 工作日交易时段内
- **WHEN** 当前美东时间为周三 10:30
- **THEN** `isUSMarketOpen()` 返回 `True`

#### Scenario: 工作日盘前
- **WHEN** 当前美东时间为周三 08:00
- **THEN** `isUSMarketOpen()` 返回 `False`

#### Scenario: 周末
- **WHEN** 当前美东时间为周六 12:00
- **THEN** `isUSMarketOpen()` 返回 `False`

### Requirement: 闭市休眠
系统 SHALL 在 `isUSMarketOpen()` 返回 `False` 时跳过扫描循环，休眠至下一个检查点。

#### Scenario: 闭市期间不扫描
- **WHEN** 当前为闭市时段
- **THEN** 扫描循环 `sleep` 并跳过所有 API 调用

### Requirement: 每日心跳
系统 SHALL 在美东 09:20 (开盘前 10 分钟) 发送心跳通知，包含进程 PID、Watchlist 数量、Redis 连通性。

#### Scenario: 心跳推送
- **WHEN** 到达美东 09:20
- **THEN** 通过微信通道发送 "🟢 AlphaTheta Scanner 存活 | 监控池: 12 只 | Redis: OK"
