## Why

AlphaTheta v2 的"信号与执行"页面目前只能处理 **单腿期权** 的 AI 推荐（Sell Put / Sell Call）。随着用户经验成长，他们需要构建 **任意复杂多腿期权组合**（Iron Condor, Calendar Spread, Buy-Write, Ratio Back Spread 等）。这些需求在现有架构下无法实现——没有通用的多腿状态管理、没有全量期权链查询、也没有不依赖硬编码公式的盈亏推演引擎。

**Why now**: ESM 模块化重构 (Phase 1-4) 已完成，前端架构足以支撑此级别的复杂交互。同时，用户明确要求"上帝视角"级别的策略控制权。

## What Changes

- **[NEW]** 前端 Strategy Studio 页面：多腿状态数组 (`currentLegs[]`) 的双向绑定与动态 DOM 管理
- **[NEW]** 通用分段线性盈亏引擎：遍历数千个价格点，叠加每条腿的到期日内在价值，提取 Max Profit / Max Loss / Break-even Points
- **[NEW]** 迷你期权链面板：T 型报价表 (Call 左、Put 右)，点击 Bid/Ask 自动填入 strike + price
- **[NEW]** 策略模板系统：Buy-Write, Iron Condor, Calendar Spread 等预设骨架，一键覆写 `currentLegs`
- **[NEW]** 后端 API：全量期权链查询 (`/api/v1/market/option_chain_mini`), 策略模板 (`/api/v1/strategy/templates`)
- **[NEW]** 情景推演卡片：实时显示 Max Profit, Max Loss, Est. Collateral, Break-even Points
- **[MODIFY]** Signal 页面重构为 Strategy Studio，保留 AI 推荐接入口

## Capabilities

### New Capabilities

- `multi-leg-state`: 多腿期权组合的状态树管理 — currentLegs[] 数组 CRUD、买/卖 · Call/Put/Stock 切换、双向绑定渲染、Net Premium 实时计算
- `universal-payoff-engine`: 通用分段线性盈亏推演引擎 — 数千价格点扫描、每腿到期内在价值叠加、Max Profit/Loss/Break-even 特征提取（严禁硬编码策略公式）
- `option-chain-api`: 后端全量期权链与组合模板 API — yfinance 调用、按日期+Ticker 查询上下各 5 档 Call/Put Bid/Ask、策略模板 JSON

### Modified Capabilities

_(none — 这是全新能力，不修改现有 spec)_

## Impact

- **前端**: 新增 `js/views/strategy_studio.js` (取代/扩展 signal.js)，新增 `js/utils/payoff-engine.js`
- **后端**: 新增 `app/routers/market_data.py` (期权链 API)，扩展 `app/routers/strategy.py` (模板 API)
- **HTML**: `index.html` 中 signal 的 `view-signal` section 改造为 Strategy Studio DOM 结构
- **依赖**: 后端依赖 `yfinance` (已有)；前端无新依赖
- **路由**: 侧边栏 "信号与执行" Tab ID 保持 `signal`，内部内容升级为 Strategy Studio
