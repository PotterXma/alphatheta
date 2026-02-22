## Context

AlphaTheta 已有 CRO v2 风控引擎（7条 Kill Switch + Limit_Price_Chaser 执行方案 + 3向情景剧本），但始终输出固定的 Buy-Write 组合建仓信号。现实中，不同多空情绪下最优单一动作差异巨大。本设计新增一层"智能择时决策树"，在 CRO 风控评估之前先行判定"今天最该执行的一个动作"。

现有架构：`renderSignal()` → `evaluateTradeProposal()` → `renderCRO()`。
新架构：`renderSignal()` → `evaluateTimingDecision()` → `evaluateTradeProposal()` → `renderCRO()`。

## Goals / Non-Goals

**Goals:**
- 基于 RSI-14、SMA200 距离、VIX、持仓状态输出唯一最优动作（Buy Stock / Sell Call / Sell Put / Buy-Write / Hold）
- VIX > 35 时强制观望，覆盖所有其他逻辑
- 在 Signal 视图新增"推荐操作"面板，清晰展示决策结果和理由
- 与现有 CRO 风控引擎无缝叠加（择时决策 → 风控复核 → 执行方案）

**Non-Goals:**
- 不替换现有 7 条 Kill Switch 规则
- 不引入后端/API 调用（保持纯前端 mock 数据架构）
- 不实现多标的同时择时（仅当前信号标的）
- 不做回测引擎

## Decisions

### 1. 决策树架构：纯函数 + 4 场景穷举

采用 `evaluateTimingDecision(marketContext, signal)` 纯函数，按以下优先级穷举：

| 优先级 | 条件 | 动作 |
|--------|------|------|
| 0 (最高) | VIX > 35 | Hold（强制观望） |
| 1 | RSI < 40 且无仓位 | Sell Put ONLY 或 Buy Stock ONLY |
| 2 | RSI > 60 且有仓位 | Sell Call ONLY |
| 3 | RSI > 60 且无仓位 | Hold（空仓观望）或 Sell 极深虚值 Put |
| 4 | RSI 40-60 且无仓位 | Buy-Write 组合建仓 |
| fallback | 其他 | Hold |

**替代方案考虑：** 评分加权系统 → 过度复杂，4 场景穷举可解释性更强，与 CRO 的审计属性匹配。

### 2. 数据流：决策树在风控之前执行

```
evaluateTimingDecision() → recommended_action
                ↓
evaluateTradeProposal(action) → is_approved + plan
                ↓
renderCRO(timing + risk) → UI
```

择时引擎输出 `recommended_action`，然后 CRO 对这个动作做风控复核。如果风控否决，UI 显示否决理由而不执行。

### 3. UI 布局：在 CRO badge 上方插入"推荐操作"面板

推荐操作面板包含：
- 动作类型 badge（颜色编码：Buy=emerald, Sell Call=cyan, Sell Put=amber, Hold=gray）
- 执行细节描述
- 场景判据摘要（RSI 值、VIX 值、持仓状态）

### 4. Mock 数据扩展策略

在 `MOCK_DATA.marketContext` 中新增字段，保持向后兼容：
- `rsi_14`: 55 (默认震荡市)
- `distance_to_sma200`: 9.71 (%)
- `current_position`: "100 shares" / "0 (cash)"
- `available_cash`: 45000
- `call_strike` / `call_premium`: 从现有 signal 派生
- `put_strike` / `put_premium`: 新增

## Risks / Trade-offs

- **[风控冲突]** 择时建议 Sell Put 但风控否决 → UI 需清晰展示"择时推荐卖 Put 但被风控否决"，用户不困惑 → 使用分层 badge（推荐操作 badge + 风控 badge 并列）
- **[场景覆盖不全]** RSI 40-60 且已有仓位未明确规则 → fallback 到 Hold，等待更极端信号
- **[Mock 数据固定]** 默认 RSI=55 + 有仓位 → 永远走场景 D 或 B → 提供 UI 控件让用户手动切换场景测试（speculation: 可在 Sandbox 中实现，本期不做）
