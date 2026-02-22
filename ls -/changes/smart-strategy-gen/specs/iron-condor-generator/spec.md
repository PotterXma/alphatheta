## Overview

防爆仓铁鹰算法 — 基于离散期权链精确寻址行权价，强制 $5 固定翼宽锁死最大风险敞口，拒绝虚假报价。

## Requirements

### R1: generateIronCondor(spotPrice, optionChainData)

纯函数，接收:
- `spotPrice: number` — 当前标的价格
- `optionChainData: { calls: [{strike, bid, ask}], puts: [{strike, bid, ask}] }` — 真实期权链

返回 `currentLegs` 格式的 4 腿数组，或抛异常。

### R2: Short Leg 寻址 (±5% Spot)

- Short Put: 在 puts 中找到距离 `spot * 0.95` **最近**的离散行权价
- Short Call: 在 calls 中找到距离 `spot * 1.05` **最近**的离散行权价
- 如果找不到符合条件的行权价 → 抛出异常

### R3: Long Leg 寻址 ($5 Fixed Wing Width)

- Long Put: 在 puts 中找 `shortPutStrike - $5` (或最接近的低档)
- Long Call: 在 calls 中找 `shortCallStrike + $5` (或最接近的高档)
- **绝不使用百分比！** 固定 $5 档位
- 如果找不到 → 抛出异常

### R4: 真实报价填充

- 卖出腿 `action: 'sell'` → `price = Bid` (卖价总是 Bid)
- 买入腿 `action: 'buy'` → `price = Ask` (买价总是 Ask)
- 如果 Bid 或 Ask 为 0/null/undefined → 抛出异常 "流动性不足"

### R5: 环境分发器 autoSuggestNeutralStrategy

- `ivRank >= 50` → 调用 `generateIronCondor`
- `ivRank < 50` → 返回 `{ success: false, reason: 'IV 过低...' }`

### R6: UI 联动流程

1. 用户点击 → 显示 `⏳ 正在智能组装...` 加载态
2. `fetch(/api/v1/market_data/option_chain_mini)` 获取真实链
3. 调用 `autoSuggestNeutralStrategy`
4. 成功 → 覆写 `currentLegs` + 渲染推演 + 显示成功提示
5. 失败 → 黄色警告 + 保留空白构建器

### R7: 异常分类

| 异常类型 | 触发条件 | 用户提示 |
|---------|---------|---------|
| NO_SHORT_PUT | Puts 链中无 ≈95% 行权价 | "期权链行权价范围不足" |
| NO_SHORT_CALL | Calls 链中无 ≈105% 行权价 | "期权链行权价范围不足" |
| NO_WING | 找不到 $5 Wing 档位 | "期权链间距过大" |
| NO_LIQUIDITY | Bid/Ask 为 0 | "流动性不足，拒绝生成" |
| IV_TOO_LOW | ivRank < 50 | "IV 过低，建议观望" |
