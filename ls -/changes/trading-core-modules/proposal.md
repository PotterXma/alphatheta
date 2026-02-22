## Why

AlphaTheta v2 的 UI 骨架已成，但三大核心交易模块仍是空壳：沙盒没有真实期权定价引擎、展期操作缺乏组合单限价预览、绩效曲线不是盯市净值（只画了现金流）。对于期权卖方策略而言，这三块直接关系到 P&L 准确性和实盘执行安全。需要一次性点亮这三大模块。

## What Changes

### Phase 1: 策略推演沙盒
- **新增** 纯 JS Black-Scholes 定价模块 (d1/d2 → Call/Put 理论价 + Greeks)
- **新增** IV 滑块 (与现有 DTE 滑块并列)
- **新增** ECharts 绘制到期日盈亏折线 + T+0 理论盈亏曲线
- **新增** Greeks 实时面板 (Delta, Gamma, Theta, Vega)

### Phase 2: 展期组合单
- **新增** 暗黑玻璃态展期 Modal (旧仓成本 + 新仓收入 + Net Credit/Debit 高亮)
- **新增** 限价微调输入框 (拒绝市价单)
- **新增** `POST /api/v1/orders/roll_combo` — 组合单 API (Buy to Close + Sell to Open 原子事务)
- **新增** TransactionLedger 双腿写入 (防单腿成交)

### Phase 3: 盯市净值曲线
- **新增** `PortfolioSnapshot` 模型 (每日跑批: 现金 + 持仓清算市值)
- **新增** `GET /api/v1/portfolio/equity-curve` — 时间序列 API
- **新增** ECharts 发光蓝色平滑折线 + Tooltip (现金占比 + 浮动市值)

## Capabilities

### New Capabilities
- `sandbox-bs-engine`: Black-Scholes 定价引擎 + ECharts 盈亏图 + IV/DTE 推演 + Greeks 面板
- `roll-combo-order`: 展期组合单 API + 限价预览 Modal + TransactionLedger 原子写入
- `mtm-equity-curve`: 盯市净值曲线 API + PortfolioSnapshot 模型 + ECharts 可视化

### Modified Capabilities
- (无已有 spec 需修改)

## Impact

- **前端新增**: `app.js` (BS 计算模块 + 沙盒重构 + Roll Modal + Equity Chart)
- **前端修改**: `index.html` (IV 滑块 + Greeks 面板 + Roll Modal + Equity Chart 容器), `style.css` (Roll Modal + Greeks 面板样式)
- **后端新增**: `routers/execution.py` (roll_combo), `routers/portfolio.py` (equity-curve), `models/portfolio_snapshot.py`
- **DB 新增**: `portfolio_snapshots` 表, `transaction_ledger` 表
- **依赖**: ECharts (已引入 CDN), 标准正态分布 CDF (JS 实现, 无额外依赖)
