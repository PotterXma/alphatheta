## ADDED Requirements

### Requirement: 主循环周期
系统 SHALL 每 15 分钟执行一轮扫描循环。

#### Scenario: 正常循环
- **WHEN** 上一轮扫描完成
- **THEN** 休眠至下一个 15 分钟周期再执行

### Requirement: 阶段 1 轻量初筛
系统 SHALL 对 Watchlist 每只标的获取现价、RSI-14、IV Rank，并在每次 API 调用间加入 1-3 秒随机延迟。仅当 RSI < 35 且 IVR < 30 时进入阶段 2。

#### Scenario: 不满足初筛条件
- **WHEN** 标的 RSI = 45, IVR = 20
- **THEN** 跳过该标的，不调用期权链 API

#### Scenario: 满足初筛条件
- **WHEN** 标的 RSI = 28, IVR = 22
- **THEN** 进入阶段 2 深潜扫描

### Requirement: 阶段 2 冷却校验
系统 SHALL 在深潜前检查冷却池。同一标的同方向信号 24 小时内只推送一次。

#### Scenario: 在冷却期内
- **WHEN** SPY 的 bullish 信号 3 小时前已推送
- **THEN** 跳过推送，日志记录 "冷却期内，已拦截"

#### Scenario: 冷却期已过
- **WHEN** SPY 的 bullish 信号 25 小时前推送
- **THEN** 通过冷却校验，进入深潜

### Requirement: 阶段 2 LEAPS 深潜
系统 SHALL 调用 `findLeapsExpiration` 定位 270-540d 到期日，获取期权链，用 `validateLeapsLiquidity` 校验 Deep ITM Call (Delta ≈ 0.80)。

#### Scenario: 找到合格 LEAPS
- **WHEN** 标的有 365d 到期日且 Deep ITM Call Bid-Ask 价差在限内
- **THEN** 触发信号推送 + 写入冷却池

#### Scenario: 无合格 LEAPS 到期日
- **WHEN** 标的最远到期日仅 180d
- **THEN** 跳过该标的，日志记录原因

### Requirement: 单标的异常隔离
系统 SHALL 将每只标的的扫描包裹在独立 try-except 中。单标的的网络超时不得导致循环终止。

#### Scenario: 单标的 API 超时
- **WHEN** NVDA 的 yfinance 请求超时
- **THEN** 日志记录错误，继续扫描下一只标的

### Requirement: API 重试
系统 SHALL 对失败的 API 请求重试最多 3 次，使用指数退避 (1s, 2s, 4s)。

#### Scenario: 第二次重试成功
- **WHEN** 第一次请求 429 失败
- **THEN** 等待 1s 后重试，第二次成功，正常处理
