## Phase 1: 核心引擎 (已完成 ✅)

- [x] 1.1 通用盈亏引擎 `js/utils/payoff-engine.js`
  - [x] 自适应步长 (spot × 0.001)
  - [x] 动态包裹边界 (Deep OTM 修复)
  - [x] 每腿到期盈亏叠加 (Call/Put/Stock × Buy/Sell)
  - [x] 边界斜率无限检测 (leftSlope/rightSlope + tolerance)
  - [x] 线性插值 Break-even
  - [x] Net Premium 计算

- [x] 1.2 行权价吸附 `js/utils/market-helpers.js`
  - [x] `snapToStrike()` — ATM 索引 + step 偏移 + clamp
  - [x] `resolveTemplate()` — strikeStep → 绝对价, dteOffset → 绝对日期
  - [x] `fetchOptionChainMini()` — 30s Map 缓存
  - [x] `fetchExpirations()` — 到期日列表

- [x] 1.3 策略模板 `js/utils/strategy-templates.js`
  - [x] Buy-Write, Cash-Secured Put, Bull Put Spread
  - [x] Iron Condor, Long Straddle, Protective Put
  - [x] Calendar Spread (Put/Call), Diagonal Spread
  - [x] strikeStep + dteOffset 设计

- [x] 1.4 引擎测试 `js/utils/test-engines.mjs`
  - [x] 47/47 测试通过 (含 Deep OTM 回归)

---

## Phase 2: 后端 API (已完成 ✅)

- [x] 2.1 期权链迷你接口 `app/routers/market_data.py`
  - [x] `GET /api/v1/market_data/option_chain_mini?ticker=&date=`
  - [x] yfinance 调用 + 现价 ±5 档过滤
  - [x] 返回 strike/bid/ask/lastPrice/volume/openInterest
  - [ ] Redis 60s 缓存 (deferred — 前端 30s Map 缓存已实现)

- [x] 2.2 到期日列表接口
  - [x] `GET /api/v1/market_data/expirations?ticker=`
  - [x] yfinance `ticker.options` 返回可用日期

- [x] 2.3 策略模板接口
  - [x] `GET /api/v1/market_data/templates`
  - [x] 返回 STRATEGY_TEMPLATES JSON (同前端)

---

## Phase 3: 前端 Strategy Studio UI (已完成 ✅)

### 3.1 HTML 结构 (`index.html`)
- [x] 替换 `view-signal` section 内部 DOM
- [x] 策略模板下拉框
- [x] 多腿容器 `#legsContainer`
- [x] 操作按钮: [添加腿] [清空]
- [x] 右侧情景推演卡片:  Net Premium / Max Profit / Max Loss / Break-even / Est. Collateral
- [x] 底部盈亏曲线图 (ECharts)

### 3.2 多腿管理器 (`js/views/strategy_studio.js`)
- [x] `currentLegs[]` 状态数组初始化
- [x] `addLeg()` — 默认 Sell Put ATM
- [x] `removeLeg(id)` — 按 UUID 删除
- [x] `updateLeg(id, patch)` — 部分更新
- [x] `renderLegs()` — 全量 DOM 重绘 (事件委托)
- [x] 每条 Leg UI 控件:
  - [x] [Buy/Sell] 切换按钮
  - [x] [Call/Put/Stock] 切换
  - [x] 到期日选择器 (fetch expirations → dropdown)
  - [x] 行权价输入 (点击展开迷你期权链)
  - [x] 数量输入 (number input)
  - [x] [删除 🗑️] 按钮
- [x] 策略模板下拉框 → `loadTemplate()` → 覆写 `currentLegs`
- [x] 任何 Leg 变动 → `recalcPayoff()` 级联刷新

### 3.3 迷你期权链面板
- [x] 就地毛玻璃浮层 (click 行权价输入 → show)
- [x] T 型报价: 左 Call (Bid/Ask) | 中 Strike | 右 Put (Bid/Ask)
- [x] 点击 Bid/Ask → 自动填入 strike + price
- [x] 外部点击关闭

### 3.4 盈亏曲线 (ECharts)
- [x] 调用 `calculateComboPayoff()` 获取 pricePoints + payoffData
- [x] 渲染分区:  绿色 (>0 区域), 红色 (<0 区域)
- [x] 标注 Break-even 点 (markLine)
- [x] 标注 Max Profit / Max Loss (markPoint)
- [x] 现价竖线 (markLine dashed)

### 3.5 情景推演卡片
- [x] Net Premium 实时显示 (Credit 绿 / Debit 红)
- [x] Max Profit 显示 (数字或 "Unlimited")
- [x] Max Loss 显示 (数字或 "Unlimited Risk")
- [x] Break-even Points 列表
- [x] Est. Collateral 显示

---

## Phase 4: 集成与验证 (已完成 ✅)

- [x] 4.1 `main.js` 注册 strategy_studio view (替换/扩展 signal)
- [x] 4.2 Dockerfile (js/ 已在上一个 change 中配置 COPY)
- [ ] 4.3 端到端测试 (需手动验证):
  - [ ] 加载 Iron Condor 模板 → 验证 4 腿渲染
  - [ ] 手动添加/删除腿 → 验证 Net Premium 实时更新
  - [ ] 点击行权价 → 验证迷你期权链面板
  - [ ] 切换 Tab → 验证 ECharts resize
  - [ ] Deep OTM 策略 → 验证 Unlimited Risk 检测
