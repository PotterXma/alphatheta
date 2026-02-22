## Capability: sandbox-bs-engine
Black-Scholes 定价引擎 + ECharts 盈亏图 + IV/DTE 推演 + Greeks 面板

### Requirement: BS-01 — Black-Scholes 纯 JS 定价模块
- 实现 `bsPrice(S, K, T, r, sigma, optionType)` 返回期权理论价
- `S`: 标的现价, `K`: 行权价, `T`: 剩余时间 (年), `r`: 无风险利率, `sigma`: IV
- 使用 Abramowitz & Stegun 近似实现 `normalCDF(x)`，精度 < 1e-7
- 默认无风险利率 `r = 0.05`

### Requirement: BS-02 — Greeks 计算
- `bsDelta(S, K, T, r, sigma, type)` → Put Delta ∈ [-1, 0]
- `bsGamma(S, K, T, r, sigma)` → 底层价格敏感度 (Call/Put 相同)
- `bsTheta(S, K, T, r, sigma, type)` → 每日时间损耗 (除以 365)
- `bsVega(S, K, T, r, sigma)` → IV 变动 1% 的价格影响

### Requirement: BS-03 — IV 滑块
- 在现有 DTE 滑块旁新增 IV 滑块
- 范围: 5% - 120%，步进 1%，默认 30%
- 标签实时显示当前 IV 值

### Requirement: BS-04 — ECharts 盈亏双曲线
- X 轴: 标的价格 (Strike ± 30%)
- Series 1 `Expiry P/L`: 到期日盈亏折线 (分段线性)
- Series 2 `T+0 P/L`: 当前 DTE/IV 下的理论盈亏曲线 (`smooth: true`)
- Y=0 水平标记线 (`markLine`)
- 滑块拖动时平滑实时重绘

### Requirement: BS-05 — Greeks 实时面板
- 图表下方横排 4 个 glass-card 小卡片
- 每个卡片: 名称 + 数值 + 单位说明
- Delta (Δ), Gamma (Γ), Theta (Θ per day), Vega (ν per 1% IV)
- 随滑块拖动实时更新

#### Scenario: covered-call 策略
- 用户选择 Covered Call
- DTE=45, IV=30%, Strike=460, Spot=450, Premium=5.20
- 到期日盈亏: 折线从 (-450+5.20) 到 (460-450+5.20)=15.20 封顶
- T+0 曲线: BS 理论价曲线

#### Scenario: IV 变化推演
- 用户将 IV 从 30% 拖到 50%
- T+0 曲线向上移动 (卖方亏损增大)
- Vega 值增大
- 到期日曲线不变 (不受 IV 影响)
