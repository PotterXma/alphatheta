## 1. Front-End UI & Mock Data Fix

- [x] 1.1 Fix VIX `undefined`: `MOCK_DATA.radar.vix.value` → `MOCK_DATA.radar.vix`
- [x] 1.2 Align premium badge with limit price ($5.20 → $520)
- [x] 1.3 Fix rationale text: "可用现金" → "可用购买力（含保证金）"
- [x] 1.4 Add Net Debit display: `(underlying - limitPrice) * 100` with cyan glow style
- [x] 1.5 Add VIX badge binding to `MOCK_DATA.marketContext`

## 2. Backend DTO Extension (`schemas/order.py`)

- [x] 2.1 Add `ComboLeg` model: conid, action, ratio, sec_type
- [x] 2.2 Add `is_combo`, `combo_legs`, `net_price` to `OrderCreate`
- [x] 2.3 Add model validator: `is_combo=True` requires `combo_legs` non-empty

## 3. Broker Combo Adapter

- [x] 3.1 Add `submit_combo_order()` abstract method to `BrokerAdapter`
- [x] 3.2 Implement Tradier multileg adapter
- [x] 3.3 Implement Paper adapter stub

## 4. Docker Rebuild & Verification

- [x] 4.1 Rebuild Docker images
- [x] 4.2 Verify API starts without import errors
- [x] 4.3 Verify frontend renders Net Debit
