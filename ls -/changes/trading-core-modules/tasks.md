## Phase 1: 策略推演沙盒 (sandbox-bs-engine)

### 1.1 Black-Scholes JS 引擎
- [x] 1.1.1 在 `app.js` 中实现 `normalCDF(x)` — Abramowitz & Stegun 近似 (精度 < 1e-7)
- [x] 1.1.2 实现 `bsPrice(S, K, T, r, sigma, type)` — 返回 Call/Put 理论价格
- [x] 1.1.3 实现 `bsDelta(S, K, T, r, sigma, type)` — Put Delta ∈ [-1, 0]
- [x] 1.1.4 实现 `bsGamma(S, K, T, r, sigma)` — 价格二阶导数
- [x] 1.1.5 实现 `bsTheta(S, K, T, r, sigma, type)` — 每日时间损耗 (÷365)
- [x] 1.1.6 实现 `bsVega(S, K, T, r, sigma)` — IV 变动 1% 的价格影响

### 1.2 IV 滑块 UI
- [x] 1.2.1 在 `index.html` Sandbox 区域的 DTE 滑块旁新增 IV 滑块 (range: 5-120, step: 1, default: 30)
- [x] 1.2.2 添加 IV 标签实时显示当前值 `<span id="ivDisplay">30%</span>`

### 1.3 ECharts 盈亏双曲线
- [x] 1.3.1 在 `app.js` 中实现 `PayoffChartManager.init()` — 初始化 ECharts 实例 (dark theme, transparent bg)
- [x] 1.3.2 实现 `_calcExpiryPayoff(strategy, strike, premium, spotRange)` — 到期日盈亏折线数据
- [x] 1.3.3 实现 `_calcT0Payoff(S, K, T, r, sigma, premium, strategy, spotRange)` — T+0 BS 理论盈亏曲线
- [x] 1.3.4 实现 `recalcAll()` — 读取所有滑块值 → 计算双曲线 + Greeks → `chart.setOption()`
- [x] 1.3.5 绑定 DTE/IV 滑块 `input` 事件 → `recalcAll()`，实现平滑实时重绘

### 1.4 Greeks 实时面板
- [x] 1.4.1 在 `index.html` 图表下方添加 4 个 glass-card (Delta Δ, Gamma Γ, Theta Θ, Vega ν)
- [x] 1.4.2 在 `style.css` 添加 Greeks 面板横排 CSS (flex, glassmorphism)
- [x] 1.4.3 `recalcAll()` 中同步更新 Greeks DOM 数值

---

## Phase 2: 展期组合单 (roll-combo-order)

### 2.1 展期 Modal UI
- [x] 2.1.1 在 `index.html` 添加 Roll Modal HTML (glass 弹窗, 旧仓信息 + 新仓输入 + Net Credit/Debit)
- [x] 2.1.2 在 `style.css` 添加 Roll Modal CSS (暗黑玻璃态, 模糊背景)
- [x] 2.1.3 在 `app.js` 实现 `RollManager.openModal(orderId)` — 填充旧仓数据 + 监听输入
- [x] 2.1.4 实现 Net Credit/Debit 实时计算 (新 ask - 旧 bid) + 高亮配色 (绿 credit / 红 debit)
- [x] 2.1.5 实现限价微调输入框逻辑 (Net Limit Price, 拒绝空值)
- [x] 2.1.6 绑定 "全程跟踪" 页的展期按钮 → `RollManager.openModal()`

### 2.2 后端 Roll API
- [x] 2.2.1 创建 `backend/app/models/transaction.py` — TransactionLedger 模型 (+ LegType enum)
- [x] 2.2.2 创建 `backend/app/routers/execution.py` — `POST /api/v1/orders/roll_combo`
- [x] 2.2.3 实现原子事务: 旧 Order → CANCELLED + 新 Order → PENDING + Ledger 双条目
- [x] 2.2.4 注册 execution router 到 `main.py`
- [x] 2.2.5 创建 `transaction_ledger` DB 表 (含 leg_type enum)

### 2.3 前端提交
- [x] 2.3.1 实现 `RollManager.submitRoll()` — POST 到 `/api/v1/orders/roll_combo`
- [x] 2.3.2 成功: 关闭 Modal + toast 通知 + 刷新持仓表
- [x] 2.3.3 失败: toast 显示错误消息

---

## Phase 3: 盯市净值曲线 (mtm-equity-curve)

### 3.1 后端模型与 API
- [x] 3.1.1 创建 `backend/app/models/portfolio_snapshot.py` — PortfolioSnapshot 模型
- [x] 3.1.2 创建 `portfolio_snapshots` DB 表
- [x] 3.1.3 创建 `backend/app/routers/portfolio.py` — `GET /api/v1/portfolio/equity-curve`
- [x] 3.1.4 实现 summary 计算 (total_return, max_drawdown, sharpe_ratio)
- [x] 3.1.5 注册 portfolio router 到 `main.py`

### 3.2 前端 ECharts 渲染
- [x] 3.2.1 在 `index.html` Lifecycle 区域添加 equity-curve-chart 容器
- [x] 3.2.2 在 `app.js` 实现 `EquityCurveManager.init()` — ECharts 初始化 (cyan 发光折线 + areaStyle)
- [x] 3.2.3 实现 `fetchAndRender()` — 调 API → 数据映射 → `chart.setOption()`
- [x] 3.2.4 实现 Tooltip 格式: 日期 + Total Equity + 现金占比 + 浮动市值

### 3.3 数据种子 (开发验证)
- [x] 3.3.1 编写种子脚本生成 90 天 mock PortfolioSnapshot 数据
- [x] 3.3.2 验证: API 返回正确 JSON + ECharts 渲染曲线

---

## 验证

- [x] V1 Phase 1: DTE/IV 滑块拖动 → 双曲线实时重绘 + Greeks 数值更新
- [x] V2 Phase 2: Roll Modal 打开 → Net Credit 计算 → 提交 → DB 写入双条目
- [x] V3 Phase 3: Equity curve API 返回 + ECharts 发光折线 + Tooltip 正确
- [x] V4 Docker rebuild + 全部新 API 返回 200
