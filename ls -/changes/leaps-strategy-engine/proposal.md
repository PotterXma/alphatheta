## Why

AlphaTheta v2 的交易哲学已发生根本性转向：从短期 Theta 收割 (铁鹰、信用价差, DTE 20-45 天) 全面转向**长周期、带杠杆的价值投资 (LEAPS)**。目标持仓周期锁定 270-540 天。原有的策略组装引擎 (`autoAssembleStrategy`)、流动性校验、日期寻址、推荐卡片渲染均围绕短期设计，无法支撑远期期权的流动性特征和 Delta/Vega 敏感度，必须进行底层重构。

## What Changes

- **新增** `findLeapsExpiration()` — 远期目标日期寻址器，在 270-540 天窗口中定位最优 LEAPS 到期日 (甜点 ≈ 365 天)
- **重写** `validateLeapsLiquidity()` — 废弃 $0.50 绝对限价，改用 $3.00 绝对 + 15% 相对双重熔断
- **重写** `autoAssembleStrategy()` 路由分发器：
  - Bullish → Deep ITM Call (Δ≈0.80) / PMCC 对角价差
  - Bearish → Deep ITM Put (Δ≈-0.70) / Put Spread
  - Neutral → **主动拦截** (远期铁鹰 Theta 无效)
- **移除** 短期策略依赖：Iron Condor、Bull Put Spread、Bear Call Spread 不再作为自动推荐策略
- **更新** 推荐卡片渲染，显示 LEAPS 标识 + DTE badge
- **更新** 成功状态栏，显示远期策略名称 + 锁定趋势提示

## Capabilities

### New Capabilities
- `leaps-date-finder`: 远期目标日期寻址算法，在离散期权链中定位 270-540 天最优到期日
- `leaps-liquidity-circuit-breaker`: 远期期权专用流动性熔断器，$3.00 绝对 + 15% 相对双重验证
- `leaps-strategy-dispatcher`: LEAPS 智能策略分发器，Deep ITM Call/Put 方向路由 + 中性拦截

### Modified Capabilities
_(无现有 specs 需要修改)_

## Impact

- **`js/utils/strategy-generator.js`** — 核心重构目标，所有策略逻辑重写
- **`js/views/strategy_studio.js`** — 推荐卡片渲染 + 日期选择 + 状态栏 + LEAPS badge
- **`js/utils/market-helpers.js`** — `fetchExpirations` / `fetchOptionChainMini` 已有 Redis 缓存支持，无需改动
- **后端无变更** — 数据层 (Redis 缓存 + yfinance) 已就绪
