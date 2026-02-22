# Smart Strategy Generator — 防爆仓铁鹰一键生成

## Why

Strategy Studio 目前只支持手动构建腿和模板加载（Iron Condor 模板用估算价格），缺乏**基于真实期权链数据**的智能策略生成能力。实盘中如果使用虚假价格和拍脑袋百分比，保证金计算会严重失真，导致爆仓风险。

需要一个生成器：读取真实 Bid/Ask → 固定翼宽 ($5) → 锁死最大风险敞口 → 拒绝低 IV 环境下强行卖权。

## What Changes

1. **新模块 `js/utils/strategy-generator.js`**: 纯函数 `generateIronCondor(spot, chainData)` + 环境分发器 `autoSuggestNeutralStrategy(tickerData, chainData)`
2. **视图联动 `js/views/strategy_studio.js`**: 从推荐标的触发 → 拉取真实期权链 → 调用生成器 → 覆写 currentLegs → 触发图表推演
3. **无后端变更**: 全部前端纯函数，复用已有 `/api/v1/market_data/option_chain_mini` API

## Capabilities

- **iron-condor-generator**: 离散期权链精确寻址 + $5 固定翼宽 + 真实 Bid/Ask 填充 + IV 路由

## Impact

- `js/utils/strategy-generator.js` — [NEW] 核心生成器
- `js/views/strategy_studio.js` — [MODIFY] 增加 `onAutoSuggest()` 流程
- `index.html` — [MODIFY] 可选: 添加 "智能组装" 按钮
- `style.css` — [MODIFY] 可选: 加载态 + 警告样式
