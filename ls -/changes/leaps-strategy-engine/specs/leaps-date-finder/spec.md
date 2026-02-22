## ADDED Requirements

### Requirement: LEAPS 日期窗口定义
系统 SHALL 将 LEAPS 合格到期日定义为距今 270-540 天 (含) 的期权到期日。

#### Scenario: 到期日在窗口内
- **WHEN** 可用到期日列表包含距今 365 天的日期
- **THEN** 系统将该日期识别为合格 LEAPS 到期日

#### Scenario: 到期日在窗口外
- **WHEN** 所有可用到期日距今均小于 270 天或大于 540 天
- **THEN** 系统不返回任何合格日期

### Requirement: 最优到期日选择 — 甜点 365 天
系统 SHALL 在所有合格到期日中，选择距离 365 天最近的日期作为最优 LEAPS 到期日。

#### Scenario: 多个合格日期可用
- **WHEN** 可用到期日列表包含距今 300d、350d、380d 三个合格日期
- **THEN** 系统选择 350d 的日期 (距 365d 甜点最近)

#### Scenario: 仅一个合格日期
- **WHEN** 可用到期日列表仅包含一个距今 500d 的合格日期
- **THEN** 系统选择该 500d 日期

### Requirement: 无合格日期异常
系统 SHALL 在找不到任何 270-540 天到期日时抛出明确的业务错误。

#### Scenario: 标的缺乏远期期权链
- **WHEN** 调用 `findLeapsExpiration` 且到期日列表为空或所有日期不在 270-540d 窗口
- **THEN** 系统抛出错误 `"该标的缺乏合格的远期期权 (LEAPS) 链，无法组装长线策略。"` 并附带当前最远可用 DTE 信息

### Requirement: 返回值结构
`findLeapsExpiration` SHALL 返回包含 `date` (ISO 日期字符串) 和 `dte` (天数整数) 的对象。

#### Scenario: 正常返回
- **WHEN** 成功找到合格日期 "2027-03-19"，距今 365 天
- **THEN** 返回 `{ date: "2027-03-19", dte: 365 }`
