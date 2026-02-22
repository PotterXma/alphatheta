## Design Decisions

### D1: Black-Scholes 纯 JS 实现 (零依赖)
**Decision**: 在前端实现 BS 定价引擎，不走后端 API。

**Rationale**: BS 公式计算量极小（标准正态 CDF + exp），无需网络往返。拖滑块时需要 60fps 实时响应，API 往返延迟不可接受。使用 Abramowitz & Stegun 近似公式实现 `normalCDF`，精度 < 1e-7。

**Approach**:
- 在 `app.js` 中新增 `BlackScholesEngine` 模块
- 导出: `bsPrice(S, K, T, r, sigma, type)`, `delta()`, `gamma()`, `theta()`, `vega()`
- `T` 单位为年 (DTE/365)，`r` 默认 0.05 (Fed Funds Rate)
- 沙盒页 DTE 和 IV 滑块联动触发 `recalcAll()` → 重绘 ECharts + Greeks 面板

### D2: ECharts 盈亏图双曲线架构
**Decision**: 一个 ECharts 实例绘制两条 series：到期日盈亏 (折线) + T+0 理论盈亏 (平滑曲线)。

**Approach**:
- X轴: 标的价格 (Strike ± 30%)
- Series 1 `到期日 P/L`: 分段线性函数，仅依赖 Strike 和 Premium
- Series 2 `T+0 P/L`: 对每个 X 点调用 `bsPrice()` 计算理论价，减去开仓成本
- 零线 (Y=0) 用 `markLine` 高亮
- 滑块变化时调用 `chart.setOption()` 更新 series.data，ECharts 自动动画

### D3: Greeks 面板实时渲染
**Decision**: 将 Greeks 作为独立 DOM 区域，不嵌入 ECharts tooltip。

**Rationale**: Greeks 需要持续可见而非 hover 触发。四个指标用 glassmorphism 卡片横排，每个卡片包含名称、数值、单位说明。

### D4: 展期组合单 — 原子事务 (Combo Order)
**Decision**: `POST /api/v1/orders/roll_combo` 在单个数据库事务中同时写入 Buy to Close 和 Sell to Open 两腿，防止单腿成交风险。

**Approach**:
- 前端 Modal 展示: 旧仓 bid (预估平仓成本) + 新仓 ask (预估开仓收入) → Net Credit/Debit
- 用户可微调 Net Limit Price
- 后端在同一个 `async with session.begin():` 中:
  1. 标记旧 Order 状态为 `CANCELLED` (模拟 Buy to Close)
  2. 创建新 Order (Sell to Open, 新到期日/行权价)
  3. 写入 `TransactionLedger` 双条目 (close_leg + open_leg)
- 如果任一步骤失败，整个事务回滚

### D5: TransactionLedger 模型
**Decision**: 新建 `transaction_ledger` 表，记录每笔资金流水。

**Schema**:
```
id:           UUID PK
order_id:     UUID FK → orders.id
ticker:       VARCHAR(16)
leg_type:     ENUM('open', 'close', 'roll_close', 'roll_open')
quantity:     INTEGER
price:        FLOAT
net_amount:   FLOAT (quantity × price × multiplier)
created_at:   TIMESTAMPTZ
```

### D6: PortfolioSnapshot 跑批模型
**Decision**: 新建 `portfolio_snapshots` 表，由后台定时跑批写入每日快照。

**Rationale**: 盯市净值 = 可用现金 + Σ(活跃持仓 × 当日收盘价 × 合约乘数)。不能仅靠 API 实时算（历史数据丢失），需每日持久化。

**Schema**:
```
id:              UUID PK
snapshot_date:   DATE UNIQUE
cash_balance:    FLOAT
positions_value: FLOAT (持仓清算市值合计)
total_equity:    FLOAT (cash + positions)
position_count:  INTEGER
created_at:      TIMESTAMPTZ
```

### D7: Equity Curve ECharts 科技感样式
**Decision**: 使用 ECharts `smooth: true` + `areaStyle` + `shadowBlur` 组合，匹配项目暗黑玻璃态主题。

**Approach**:
- 折线: `#06b6d4` (cyan) + `shadowBlur: 10`
- 填充区域: 从 cyan 到透明的渐变
- Tooltip: 显示日期、Total Equity、现金占比 (%)、浮动市值
- 背景: transparent (继承 glass-card)

## File Map

| Phase | 文件 | 类型 | 用途 |
|-------|------|------|------|
| P1 | `app.js` | MOD | BlackScholesEngine 模块 + 沙盒重构 |
| P1 | `index.html` | MOD | IV 滑块 + Greeks 面板 HTML |
| P1 | `style.css` | MOD | Greeks 面板 CSS |
| P2 | `app.js` | MOD | RollManager 模块 (Modal + API 调用) |
| P2 | `index.html` | MOD | Roll Modal HTML |
| P2 | `style.css` | MOD | Roll Modal CSS |
| P2 | `backend/app/routers/execution.py` | NEW | roll_combo API |
| P2 | `backend/app/models/transaction.py` | NEW | TransactionLedger 模型 |
| P3 | `app.js` | MOD | EquityCurveManager (ECharts) |
| P3 | `index.html` | MOD | Equity Chart 容器 |
| P3 | `backend/app/routers/portfolio.py` | NEW | equity-curve API |
| P3 | `backend/app/models/portfolio_snapshot.py` | NEW | PortfolioSnapshot 模型 |
