# Studio Smart Dispatcher — 推荐面板 + 风控路由 + 熔断机制

## Why

策略工作室在之前的重构中失去了"🏆 智能推荐 Top 3"区块。同时，当前的 `autoSuggestNeutralStrategy` 仅支持中性 (Iron Condor)，不具备方向性策略路由和风控熔断。

## What Changes

1. **HTML**: 在 `.studio-container` 上方恢复推荐面板 (3 张暗黑玻璃态卡片)
2. **CSS**: 推荐卡片悬浮发光 (方向色: 绿/红/青)
3. **strategy-generator.js**: 新增 `autoAssembleStrategy()` 方向路由 + 熔断机制
4. **strategy_studio.js**: 新增 `onRecommendationCardClick()` 事件流

## Capabilities

- **recommendation-panel**: Top3 推荐区 UI
- **smart-dispatcher**: 方向路由 (bull put spread / bear call spread / iron condor) + 流动性/资金熔断

## Impact

- `index.html` — [MODIFY] 添加推荐面板 HTML
- `style.css` — [MODIFY] 推荐卡片样式
- `js/utils/strategy-generator.js` — [MODIFY] 新增 autoAssembleStrategy + circuit breakers
- `js/views/strategy_studio.js` — [MODIFY] 新增 onRecommendationCardClick + 数据流联动
