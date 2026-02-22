## ADDED Requirements

### Requirement: Bullish 路由 — Deep ITM Call
当信号方向为 `bullish` 时，系统 SHALL 组装远期深度价内 Call，行权价目标为 `spotPrice × 0.80` (近似 Δ ≈ 0.80)。

#### Scenario: 标准 Bullish 组装
- **WHEN** 信号方向为 bullish, 现价 $500, 远期 Calls 链可用
- **THEN** 系统寻找最接近 $400 的远期 Call 行权价，以 Ask 价买入 1 张

#### Scenario: Bullish 合约流动性不足
- **WHEN** 目标行权价的 Call 合约 Bid = 0
- **THEN** 系统触发流动性熔断，拒绝组装并返回错误信息

### Requirement: Bullish PMCC 可选近期卖出腿
系统 SHOULD 尝试在近期链 (30-45 DTE) 中寻找 OTM Call (Δ ≈ 0.20, 行权价 ≈ spotPrice × 1.05) 作为 PMCC 卖出腿。如果近期腿通过流动性校验则附加，否则回退为单腿策略。

#### Scenario: 近期腿可用
- **WHEN** 近期 30d 链有足够流动性的 OTM Call
- **THEN** 系统附加 Sell Call 腿，策略名称为 `leaps_pmcc`

#### Scenario: 近期腿流动性不足
- **WHEN** 近期链无可用合约或流动性不足
- **THEN** 系统仅保留远期 Buy Call 单腿，策略名称为 `leaps_deep_itm_call`

### Requirement: Bearish 路由 — Deep ITM Put Spread
当信号方向为 `bearish` 时，系统 SHALL 组装远期深度价内 Put，行权价目标为 `spotPrice × 1.30` (近似 Δ ≈ -0.70)。系统 SHOULD 同时寻找更低行权价的 Put (距 Long Put 下方 $20) 作为卖出腿以对冲 Vega。

#### Scenario: 标准 Bearish 组装 (含 Short Leg)
- **WHEN** 信号方向为 bearish, 现价 $500, 远期 Puts 链可用
- **THEN** 系统买入 $650 Put + 卖出 $630 Put (如果 Short Leg 有流动性)

#### Scenario: Short Leg 不可用
- **WHEN** Short Put 行权价的合约流动性不足
- **THEN** 系统回退为单腿 Deep ITM Put

### Requirement: Neutral 路由 — 主动拦截
当信号方向为 `neutral` 时，系统 SHALL 拒绝自动组装并返回拦截信息。

#### Scenario: Neutral 信号被拦截
- **WHEN** 信号方向为 neutral
- **THEN** 系统返回 `success: false` 并附带拦截原因: `"宏观拦截：在长达 1 年的周期内构建中性 Theta 策略资金效率极低，已拒绝自动组装。"`

### Requirement: 保证金穿透熔断
系统 SHALL 在策略总成本超过可用购买力 30% 时拒绝组装。

#### Scenario: 策略成本超出购买力
- **WHEN** 策略净支出 $15,000, 可用购买力 $45,000 (33% > 30%)
- **THEN** 系统拒绝组装并返回保证金穿透警告

### Requirement: LEAPS 腿标记
系统 SHALL 在所有远期腿的数据对象上添加 `_leaps: true` 标记。

#### Scenario: 生成的腿包含 LEAPS 标记
- **WHEN** 策略组装成功
- **THEN** 每条远期期权腿的对象包含 `_leaps: true` 属性

### Requirement: 返回值包含 DTE 信息
`autoAssembleStrategy` 成功返回时 SHALL 包含 `leapsDte` 字段和 `meta.isLeaps: true`。

#### Scenario: 成功返回结构
- **WHEN** Bullish 策略组装成功, 选定到期日距今 315 天
- **THEN** 返回对象包含 `leapsDte: 315` 和 `meta: { isLeaps: true, dte: 315 }`
