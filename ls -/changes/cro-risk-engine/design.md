## Context

AlphaTheta v7.0 是纯 HTML/CSS/JS SPA 仪表盘。信号视图当前直接展示交易建议并可一键执行，无独立风控审批层。CRO 引擎将作为纯前端函数插入信号渲染流程，在展示和执行之间添加风控网关。

## Goals / Non-Goals

**Goals:**
- 纯前端 `evaluateTradeProposal(proposal, market, account)` 函数，返回 JSON 审批结果
- 5 条硬性否决规则顺序校验，首条触发即短路返回
- 中间价年化收益率计算 + 7%-20% 合规区间校验
- 双向情景剧本生成（涨 15% / 跌 20%）
- 审批结果驱动 UI 渲染：通过则显示执行方案+剧本，否决则显示原因+锁定按钮
- i18n 覆盖所有新增 UI 文本

**Non-Goals:**
- 不接入真实 broker API
- 不实现动态 Greeks 实时计算
- 不做历史回测

## Decisions

### 1. 评估函数纯同步设计

**选择**: `evaluateTradeProposal()` 为纯同步函数，接受 mock 数据，返回 JSON。无异步调用。

**理由**: 所有数据已在前端 mock，无需等待网络。

### 2. 否决规则顺序校验

**选择**: 5 条规则按编号顺序校验，首条触发即返回 `is_approved: false` + 对应 `rejection_reason`。

**规则顺序**:
1. 数据延迟 > 15s
2. 买卖价差 > Bid 的 15%
3. 保证金占用 > 60%
4. 除息日 < 5 天 + ITM Covered Call
5. 年化收益 不在 7%-20%

### 3. 年化收益率计算

**选择**: `annualized = (midPrice / strike) × (365 / dte) × 100`，其中 `midPrice = (bid + ask) / 2`。

### 4. 情景剧本模板化

**选择**: 剧本文本根据交易类型（Covered Call vs Cash-Secured Put）和当前参数模板化生成，不做复杂计算。

### 5. UI 集成位置

**选择**: 在信号视图的 Rationale 面板下方新增三个区域：
1. 审批状态徽章（绿色通过/红色否决）
2. 执行方案面板（限价、年化收益）
3. 情景剧本双卡片（暴涨/暴跌）

### 6. Mock 市场数据扩展

**选择**: 在 `MOCK_DATA` 中新增 `marketContext` 对象包含 `dataLatency`、`bid`/`ask`、`projectedMarginUtil`、`daysToExDividend`、`delta` 等字段。

## Risks / Trade-offs

- **纯前端计算无法反映真实市场** → 已标注为模拟，非生产系统
- **模板化剧本缺乏精确性** → 可接受，目的是展示 UI 能力而非真实对冲
- **硬编码规则阈值** → 未来可移入 Settings 视图做可配置化
