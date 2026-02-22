## 1. LEAPS 日期寻址器

- [x] 1.1 实现 `findLeapsExpiration(availableDates)` — 270-540d 窗口扫描 + 甜点 365d 择优
- [x] 1.2 无合格日期时抛出 `StrategyGenError("NO_LEAPS_DATE", ...)` 并附带最远可用 DTE 诊断信息
- [x] 1.3 返回 `{ date, dte }` 结构体

## 2. LEAPS 流动性熔断器

- [x] 2.1 重写 `validateLeapsLiquidity(bid, ask, context?)` — 零报价拦截 + 绝对 $3.00 + 相对 15% (分母 ask)
- [x] 2.2 确保校验优先级: 零报价 → 绝对价差 → 相对价差

## 3. LEAPS 智能分发器

- [x] 3.1 Bullish 路由: Deep ITM Call (`strike ≈ spot × 0.80`)，买入远期链行权价
- [x] 3.2 Bullish PMCC 可选近期卖出腿: 30-45d OTM Call (`strike ≈ spot × 1.05`)，流动性不足时回退
- [x] 3.3 Bearish 路由: Deep ITM Put Spread (`Long strike ≈ spot × 1.30`)，Short Put 距 Long 下方 $20
- [x] 3.4 Neutral 路由: 主动拦截, 返回 `{ success: false, code: "NEUTRAL_BLOCKED" }`
- [x] 3.5 保证金穿透熔断: 净支出 > 购买力 30% 时拒绝
- [x] 3.6 所有远期腿标记 `_leaps: true`，返回值包含 `leapsDte` + `meta.isLeaps`

## 4. 视图层集成 (strategy_studio.js)

- [x] 4.1 推荐卡片点击时调用 `findLeapsExpiration` 定位远期到期日，fallback 到最远可用
- [x] 4.2 推荐卡片渲染加入 `[🎯 LEAPS 长期看多/看空]` 青色 badge
- [x] 4.3 组装成功后状态栏显示: `✨ 自动装配成功: 锁定远期宏观趋势 (DTE: Xd)`
- [x] 4.4 期权腿列表旁渲染 `LEAPS: 315d` 小型 badge

## 5. 清理与验证

- [x] 5.1 移除旧版短期策略路由 (Bull Put Spread / Bear Call Spread 不再作为自动推荐)
- [x] 5.2 保留 `generateIronCondor` 和 `autoSuggestNeutralStrategy` 供手动模板使用
- [x] 5.3 重新 build + deploy web 容器
- [x] 5.4 点击推荐卡片验证: Bullish → Deep ITM Call, Bearish → Put Spread, Neutral → 拦截
