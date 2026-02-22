## Why

现有 CRO 风控引擎仅做静态合规审查（7条 Kill Switch），默认始终推荐 Buy-Write 组合建仓。但现实中，不同多空情绪下的最优动作完全不同——超卖时应该只买正股或卖 Put 而非卖 Call，超买时应该只卖 Call 而非追高买股。需要一个基于 RSI、SMA200、VIX 的智能择时决策树，让 CRO 输出"今天最该做的那一个动作"而非一刀切的组合单。

## What Changes

- 新增 `evaluateTimingDecision()` 择时决策函数，基于 RSI/SMA200/VIX/持仓状态输出单一最优动作
- 扩展 `MOCK_DATA.marketContext` 增加 `rsi_14`、`distance_to_sma200`、`current_position`、`available_cash`、`call_strike/premium`、`put_strike/premium` 字段
- 新增"推荐操作"UI 组件：在 Signal 视图中展示决策树推荐的 action_type（Buy Stock / Sell Call / Sell Put / Buy-Write / Hold）及其依据
- 重构 `renderCRO()` 以整合择时引擎的输出到现有风控面板
- 新增 VIX > 35 强制观望规则到 Kill Switch
- 新增 i18n 键覆盖所有新增 UI 文案

## Capabilities

### New Capabilities
- `timing-decision-tree`: 基于 RSI/SMA200/VIX/持仓状态的 4 场景智能择时引擎（超卖无仓、超买有仓、超买无仓、震荡无仓）
- `recommended-action-ui`: 推荐操作面板 UI — 展示决策树选择的 action_type、target_ticker、execution_details 及理由

### Modified Capabilities
- (none — 现有 CRO 评估器保持不变，择时引擎作为上层决策叠加在上面)

## Impact

- `app.js`: 新增 `evaluateTimingDecision()` 函数，扩展 `MOCK_DATA.marketContext`，修改 `renderSignal()` 和 `renderCRO()` 流程
- `index.html`: 在 Signal 视图的 CRO 区域新增推荐操作面板 HTML
- `style.css`: 新增推荐操作面板的样式
- i18n 字典两语言各约新增 8-10 个键
