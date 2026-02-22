## 1. Strategy DTOs (`schemas/strategy.py`)

- [x] 1.1 `ActionType(StrEnum)` — 6 种操作 (SELL_PUT/SELL_CALL/BUY_WRITE/BUY_TO_CLOSE/ROLL_OUT/HOLD)
- [x] 1.2 `OptionContract` — OCC 合约快照 (Greeks + OI + Volume + computed mid_price/spread_pct)
- [x] 1.3 `StrategyMarketContext` — 策略引擎输入 (has_position + earnings_date + options_chain)
- [x] 1.4 `ExecutionDetails` — 操作参数 (contract_symbol + strike + delta + dte + limit_price)
- [x] 1.5 `TimingDecision` — 引擎输出 (action_type + scene_label + confidence + reasoning)
- [x] 1.6 `PositionSnapshot` — 持仓快照 (computed dte/profit_pct/is_atm/is_itm)

## 2. Entry Engine (`services/strategy_entry.py`)

- [x] 2.1 Priority 0: VIX > 35 → HOLD (系统性风险熔断)
- [x] 2.2 Priority 1: 财报 < 3 天 → HOLD (IV Crush 规避)
- [x] 2.3 Scene A: RSI < 40 且无持仓 → SELL_PUT (超卖抄底)
- [x] 2.4 Scene B: RSI > 60 且有持仓 → SELL_CALL (超买备兑)
- [x] 2.5 Scene C: RSI > 60 且无持仓 → HOLD (拒绝追高)
- [x] 2.6 Scene D: RSI 40-60 且无持仓 → BUY_WRITE (震荡建仓)
- [x] 2.7 `_find_optimal_strike()` — Delta=0.16 寻优 + 流动性三重过滤
- [x] 2.8 模块级便捷函数 `evaluate_market_entry()`

## 3. Lifecycle Scanner (`services/strategy_lifecycle.py`)

- [x] 3.1 Rule 1: 50% Take-Profit → BUY_TO_CLOSE (Theta 衰减曲线说明)
- [x] 3.2 Rule 2: DTE ≤ 21 + 浮亏/ATM → ROLL_OUT (Gamma 爆炸防御)
- [x] 3.3 Rule 3: Deep ITM > 5% → ROLL_OUT (Assignment 风险预警)
- [x] 3.4 Per-position 短路: 止盈优先, 同一持仓只出一个信号
- [x] 3.5 模块级便捷函数 `scan_portfolio_lifecycle()`
