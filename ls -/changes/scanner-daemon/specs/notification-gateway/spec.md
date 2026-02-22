## ADDED Requirements

### Requirement: 通知管理器架构
系统 SHALL 提供 `NotificationManager` 类，支持通过配置启用/禁用各通道。所有发送方法必须为异步非阻塞，且包裹在 try-except 中 (发送失败不得终止扫描循环)。

#### Scenario: 单通道发送失败
- **WHEN** 微信推送因网络错误失败
- **THEN** 日志记录错误，不影响 Email 和 WebSocket 推送

### Requirement: WebSocket 推送
系统 SHALL 通过 WebSocket 将信号推送到前端连接的客户端。

#### Scenario: 有活跃 WebSocket 连接
- **WHEN** 前端有 1 个 WebSocket 连接在线
- **THEN** 推送 JSON 信号数据到该连接

#### Scenario: 无活跃连接
- **WHEN** 无 WebSocket 连接
- **THEN** 跳过推送，不报错

### Requirement: Email 推送
系统 SHALL 通过 SMTP 发送 HTML 格式的信号研报邮件，包含标的名、现价、RSI、LEAPS DTE、Deep ITM 行权价和成本。

#### Scenario: SMTP 配置完整
- **WHEN** 环境变量包含 SMTP_HOST, SMTP_USER, SMTP_PASS
- **THEN** 发送 HTML 邮件到配置的收件地址

#### Scenario: SMTP 未配置
- **WHEN** 环境变量缺少 SMTP_HOST
- **THEN** 跳过 Email 通道，日志记录 "Email 通道未配置"

### Requirement: 微信推送 (Server酱)
系统 SHALL 通过 Server酱 SendKey 发起 HTTP POST 推送精简信号到用户微信。

#### Scenario: Server酱推送成功
- **WHEN** SendKey 配置且网络正常
- **THEN** POST `https://sctapi.ftqq.com/{SENDKEY}.send` 成功

#### Scenario: Server酱额度用尽
- **WHEN** 返回 HTTP 429 或额度不足错误
- **THEN** 日志记录 "Server酱额度用尽"，回退到 Email 通道

### Requirement: 信号消息格式
系统 SHALL 统一信号消息格式，包含: 标的 ticker、现价、RSI-14、IV Rank、LEAPS 到期日、DTE、Deep ITM Call 行权价、Ask 价格、策略名称。

#### Scenario: 消息格式化
- **WHEN** 触发 AAPL bullish LEAPS 信号
- **THEN** 消息包含 "🎯 AAPL LEAPS 建仓信号 | $185.50 | RSI: 28 | DTE: 365d | Call $150 @ $38.50"
