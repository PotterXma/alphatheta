## universal-payoff-engine

通用分段线性盈亏推演引擎 — 严禁硬编码策略公式，必须自动处理任意腿数组合。

### Requirements

- **R1 — 自适应步长**: 生成模拟价格数组区间 `[spot * 0.5, spot * 1.5]`，步长 `spot * 0.001`，保证 ~1000 个价格点。

- **R2 — 通用到期盈亏叠加**: 对每个模拟价格 $S$，遍历 `legs` 数组，按 `action` (buy/sell) 和 `type`+`right` 叠加到期日内在价值:
  - Call Buy: `(max(0, S - K) - premium) × qty × mult`
  - Call Sell: `(premium - max(0, S - K)) × qty × mult`
  - Put Buy: `(max(0, K - S) - premium) × qty × mult`
  - Put Sell: `(premium - max(0, K - S)) × qty × mult`
  - Stock Buy: `(S - price) × qty × 1`
  - Stock Sell: `(price - S) × qty × 1`

- **R3 — 边界斜率无限检测 (Slope-Based Infinity Detection)**: 严禁仅看边界最大/最小值。必须计算:
  - `rightSlope = payoff[last] - payoff[last - 1]` (右侧边界导数)
  - `leftSlope = payoff[1] - payoff[0]` (左侧边界导数)
  - 若 rightSlope > 容差 且为全局最大 → `maxProfit = "Unlimited"`
  - 若 leftSlope < -容差 且为全局最小 → `maxLoss = "Unlimited Risk"`
  - 容差 = 步长的 0.5 (避免浮点精度误判)

- **R4 — 盈亏平衡点线性插值**: 扫描 payoff 数组找出所有相邻符号翻转点 (`pnl[i] * pnl[i+1] < 0`)。对每个翻转点使用线性插值:
  ```
  breakeven = pricePoints[i] - pnl[i] * (pricePoints[i+1] - pricePoints[i]) / (pnl[i+1] - pnl[i])
  ```
  返回数组 (可能 0 个、1 个或多个)。

- **R5 — 返回结构**: 函数返回 `{ pricePoints, payoffData, maxProfit, maxLoss, breakevens, estCollateral }` 其中 `estCollateral` = `|maxLoss|` (有限时)。

- **R6 — 纯函数，零 DOM 依赖**: 可在 Node.js 环境独立运行和测试。
