## option-chain-api

后端全量期权链查询与策略组合模板 API。

### Requirements

- **R1 — 期权链迷你接口**: `GET /api/v1/market/option_chain_mini?ticker=SPY&date=2026-04-15` 调用 `yfinance.Ticker(ticker).option_chain(date)` 返回现价上下各 5 档的 Call/Put 数据。每条记录包含: `strike`, `bid`, `ask`, `lastPrice`, `volume`, `openInterest`。

- **R2 — 可用到期日列表**: `GET /api/v1/market/expirations?ticker=SPY` 返回该 Ticker 的所有可用到期日数组。

- **R3 — 策略模板接口**: `GET /api/v1/strategy/templates` 返回策略模板 JSON 数组，每个模板包含:
  - `name`: 策略名称
  - `description`: 策略描述
  - `legs[]`: 腿骨架数组，每条腿包含 `type`, `right`, `action`, `strikeStep` (档位偏移, 非绝对值), `dteOffset` (天数偏移), `qty`

- **R4 — 行权价吸附算法 (前端)**: 纯函数 `snapToStrike(spot, strikeStep, availableStrikes)`:
  1. 在 `availableStrikes` 中找到最接近 `spot` 的 ATM 索引
  2. 按 `strikeStep` 偏移指定档位数
  3. 边界保护: 超出数组范围时 clamp 到首/末元素

- **R5 — 缓存策略**: 同一 ticker+date 组合前端缓存 30s (Map<key, {data, ts}>)。后端 Redis TTL 60s。

- **R6 — 错误处理**: yfinance 超时 → 504; 无效日期 → 400 + 可用日期列表; 无数据 → 空数组 + message。
