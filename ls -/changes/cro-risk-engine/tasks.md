## 1. CRO Evaluator Core Logic

- [x] 1.1 Add `marketContext` to `MOCK_DATA` — `dataLatency`, `bid`, `ask`, `projectedMarginUtil`, `daysToExDividend`, `delta`, `isITM`
- [x] 1.2 Implement `evaluateTradeProposal()` function with 5 kill switch rules (short-circuit on first failure)
- [x] 1.3 Implement mid-price annualized yield calculation `(midPrice/strike)×(365/dte)×100`
- [x] 1.4 Implement execution plan generation — limit price = `bid + spread×0.3`, order type "Limit"

## 2. Scenario Playbooks

- [x] 2.1 Implement `generatePlaybooks()` — bullish surge (+15%) Roll Up/Out strategy text with price targets
- [x] 2.2 Implement bearish crash (-20%) Roll Down/Out defensive strategy text with price targets
- [x] 2.3 Generate `ui_rationale` array (3 concise reasons, ≤20 chars each)

## 3. Risk UI Components

- [x] 3.1 Add CRO approval badge HTML to signal view — green "✓ 风控通过" / red "✗ 风控否决"
- [x] 3.2 Add execution plan panel HTML — order type, limit price, annualized yield
- [x] 3.3 Add dual playbook cards HTML — bullish (green accent) + bearish (red accent)
- [x] 3.4 Style all new CRO UI components (badge, plan panel, playbook cards)
- [x] 3.5 Gate execute button on CRO approval — disabled + greyed when rejected

## 4. i18n & Integration

- [x] 4.1 Add CRO-related i18n keys to both `en` and `zh` dictionaries
- [x] 4.2 Wire `evaluateTradeProposal()` into `renderSignal()` flow — evaluate before rendering, drive UI from result
- [x] 4.3 Update `renderAll()` to include CRO re-evaluation on language switch
