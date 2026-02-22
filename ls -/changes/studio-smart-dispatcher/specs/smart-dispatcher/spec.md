## Overview

方向路由 + 流动性/资金熔断 + Top3 推荐面板联动。

## Requirements

### R1: 推荐面板 HTML/CSS

- 3 张 `.recommendation-card`，包含 ticker, 现价, 推荐理由, 信号方向 (bullish/bearish/neutral)
- `backdrop-filter: blur(12px)` 暗黑玻璃态
- `:hover` 轻微上浮 + 方向色发光 (绿/红/青)

### R2: validateLiquidity(bid, ask) 流动性熔断

- 价差 `ask - bid > 0.50` OR 价差比例 `(ask-bid)/bid > 0.20 (20%)` → 抛出 `StrategyGenError("NO_LIQUIDITY",...)`

### R3: autoAssembleStrategy(ticker, direction, currentBP, chainData, exp)

方向路由:
| direction | 策略 | Short Leg | Long Leg |
|-----------|------|-----------|----------|
| bullish | Bull Put Spread | Short Put @95% | Long Put @shortPut-$5 |
| bearish | Bear Call Spread | Short Call @105% | Long Call @shortCall+$5 |
| neutral | Iron Condor (4 腿) | 使用现有 generateIronCondor |

### R4: 资金限额验证

- `maxLoss = wingWidth * 100 * quantity`
- `maxLoss > currentBP * 0.3` → 抛出 "保证金穿透警告"

### R5: onRecommendationCardClick(ticker, direction)

1. `setState('activeTicker', ticker)` → ticker 联动
2. 清空 currentLegs
3. 显示加载态
4. `fetch` 真实期权链 (bypass cache)
5. 调用 `autoAssembleStrategy`
6. 成功 → 覆写 legs + 渲染 + 成功提示
7. 失败 → 红色/黄色警告框 + 保留空白构建器
