## 1. Mock Data Extension

- [x] 1.1 Add `rsi_14: 55` to `MOCK_DATA.marketContext`
- [x] 1.2 Add `distance_to_sma200: 9.71` to `MOCK_DATA.marketContext`
- [x] 1.3 Add `current_position: "100 shares"` to `MOCK_DATA.marketContext`
- [x] 1.4 Add `available_cash: 45000` to `MOCK_DATA.marketContext`
- [x] 1.5 Add `put_strike: 505` and `put_premium: 3.80` to `MOCK_DATA.marketContext`

## 2. Timing Decision Tree Core Logic

- [x] 2.1 Implement `evaluateTimingDecision()` pure function skeleton — accepts `(marketContext, signal)`, returns `{ action_type, target_ticker, execution_details, scene_label, scene_factors }`
- [x] 2.2 Implement Priority 0: VIX > 35 → `Hold` with forced standby rationale
- [x] 2.3 Implement Priority 1 (Scene A): RSI < 40 + no position → `Sell Put ONLY` with put candidate details
- [x] 2.4 Implement Priority 2 (Scene B): RSI > 60 + has position → `Sell Call ONLY` with call candidate details
- [x] 2.5 Implement Priority 3 (Scene C): RSI > 60 + no position → `Hold` (refuse to chase)
- [x] 2.6 Implement Priority 4 (Scene D): RSI 40-60 + no position → `Buy-Write` combo
- [x] 2.7 Implement fallback: RSI 40-60 + has position → `Hold`

## 3. Integration with CRO Risk Evaluator

- [x] 3.1 Wire `evaluateTimingDecision()` call into `renderSignal()` — execute before `evaluateTradeProposal()`
- [x] 3.2 Pass timing result's `action_type` context to `evaluateTradeProposal()` for risk compliance check
- [x] 3.3 Update `renderCRO()` to accept and display both timing and risk results

## 4. Recommended Action UI Panel

- [x] 4.1 Add recommended action panel HTML to Signal view — action badge, ticker, execution details, scene factors
- [x] 4.2 Style action badge with color coding: Buy=emerald, Sell Call=cyan, Sell Put=amber, Hold=gray
- [x] 4.3 Style scene factor inline badges (RSI, VIX, position state)
- [x] 4.4 Implement `renderTimingPanel()` function to populate panel from timing result
- [x] 4.5 Hide panel gracefully if `evaluateTimingDecision()` returns null

## 5. i18n

- [x] 5.1 Add timing-related i18n keys to `zh` dictionary (~10 keys: panel title, 5 action labels, factor labels, execution templates)
- [x] 5.2 Add corresponding i18n keys to `en` dictionary
