## Context

AlphaTheta v2 的策略引擎 (`js/utils/strategy-generator.js`) 当前围绕短期信用价差 (DTE 20-45d) 设计，包含 Iron Condor、Bull Put Spread、Bear Call Spread 三种策略路由。流动性熔断阈值为绝对 $0.50 / 相对 20%，适用于短期 ATM/OTM 期权但不适用于远期深度价内合约。

团队决策将所有自动推荐策略迁移至 LEAPS 周期 (270-540d)，核心数据链路已就绪：
- Redis 缓存 + yfinance 后端：`/api/v1/market_data/expirations` (24h TTL) 和 `/api/v1/market_data/option_chain_mini` (4h TTL) 已支持远期期权链
- 前端已有 `findTargetExpiration` / `validateLiquidity` 初版实现，但需升级至生产级标准

## Goals / Non-Goals

**Goals:**
- 实现生产级 `findLeapsExpiration(availableDates)` 寻址器，精确定位 270-540d 窗口的最优到期日
- 实现远期期权专用 `validateLeapsLiquidity(bid, ask)` 熔断器
- 重写 `autoAssembleStrategy` 为纯 LEAPS 分发器：Bullish → Deep ITM Call / PMCC, Bearish → Deep ITM Put Spread, Neutral → 拦截
- 在推荐卡片和期权腿 UI 中添加显眼的 LEAPS 标识

**Non-Goals:**
- 不修改后端 API / Redis 缓存层
- 不实现自定义 DTE 范围 (硬编码 270-540d)
- 不引入真实 Greeks API — 仍通过行权价偏移量近似 Delta

## Decisions

### D1: Deep ITM 行权价定位 — 现价偏移 vs Greeks API

**选择**: 现价偏移百分比近似法

远期期权链不携带实时 Greeks 数据 (yfinance `option_chain()` 仅返回 strike/bid/ask/OI)。

| 方向 | 目标 Delta | 偏移公式 | 含义 |
|------|-----------|---------|------|
| Bullish | Δ ≈ 0.80 | `strike ≈ spot × 0.80` | 深度 ITM Call, 20% 价内 |
| Bearish | Δ ≈ -0.70 | `strike ≈ spot × 1.30` | 深度 ITM Put, 30% 价内 |

使用 `findClosestStrike(chain, targetPrice)` 在离散期权链中就近取整。

**替代方案**: 接入 CBOE/IB Greeks API → 成本高、复杂度不匹配 MVP 阶段，舍弃。

### D2: 流动性验证 — 绝对 + 相对双重门控

**选择**: 绝对 ≤ $3.00 + 相对 (ask-bid)/ask ≤ 15%

远期 Deep ITM 合约的绝对价差通常 $1-4 (正常)，但相对价差低于 10%。短期 OTM 合约绝对价差虽小 ($0.05-0.50) 但相对价差可达 50%+。

注意: 分母为 `ask` 而非 `bid` — 因为 `bid` 可能为 0 或极小，用 `ask` 更稳定。

### D3: Neutral 方向处理 — 拦截 vs 降级

**选择**: 主动拦截并抛出业务级警告

远期铁鹰 Theta 日衰减 ≈ $0.01/天 (vs 短期 $0.15/天)，锁定一年资金换取 ~$3 收入，ROI 不可接受。
直接阻断比降级为日历价差更安全 — 避免用户误以为系统推荐了有效中性策略。

### D4: PMCC 近期卖出腿 — 可选附加

**选择**: 仅在近期链 (30-45d) 有流动性时附加 Short Call

PMCC (穷人版备兑) 的完整形态是: Long LEAPS Call + Short 近期 OTM Call。
但近期 OTM Call 在非交易时段可能无流动性。设计为可选腿：如果近期 Call 通过流动性校验则附加，否则回退为单腿 Deep ITM Call。

### D5: UI 标识方案

**选择**: 双层标识

1. **推荐卡片**: 在方向标签旁加 `[🎯 LEAPS 长期看多/看空]` 青色 badge
2. **期权腿列表**: 每条腿旁显示 `LEAPS: 315d` 小型 badge
3. **成功状态栏**: `✨ 自动装配成功: 锁定远期宏观趋势 (DTE: 315天)`

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| 标的无 LEAPS 合约 (如小盘股) | `findLeapsExpiration` 抛异常，用户无法组装 | 前端 catch 后显示 "该标的不支持远期期权" 友好提示 |
| 深度 ITM 合约 OI 极低 | 大单无法成交 | 流动性熔断器拦截 Bid=0 的合约 |
| 现价偏移近似 Delta 精度不足 | 实际 Delta 可能 0.70-0.85 波动 | 对于 LEAPS 持有期来说，±0.05 Delta 偏差影响可忽略 |
| 非交易时段 yfinance 超时 | Redis 缓存降级，但首次加载可能失败 | 已有 24h/4h 缓存 + 8-10s 超时 fallback |
