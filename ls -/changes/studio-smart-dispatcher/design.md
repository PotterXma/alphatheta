## Architecture

复用现有 `strategy-generator.js` 模块，扩展方向路由。无后端变更。

## Strategy Routing

```
   direction
       │
  ┌────┴────┐
  │ bullish │ → generateBullPutSpread(spot, puts, exp)
  │ bearish │ → generateBearCallSpread(spot, calls, exp)
  │ neutral │ → generateIronCondor(spot, chain, exp)  [已有]
  └─────────┘
       │
  ┌────┴────┐
  │ Circuit │
  │ Breakers│
  └────┬────┘
  - validateLiquidity(bid, ask)  → spread > $0.50 or > 20%
  - validateMargin(maxLoss, bp)  → maxLoss > 30% BP
       │
  ┌────┴────┐
  │ Return  │ → { success: true, legs: [...], meta: {...} }
  │   or    │ → { success: false, reason: "...熔断..." }
  └─────────┘
```

## Bull Put Spread (2 腿)

```
Short Put = puts closest to spot * 0.95 → price = Bid
Long Put  = puts closest to shortPut.strike - $5 → price = Ask
```

## Bear Call Spread (2 腿)

```
Short Call = calls closest to spot * 1.05 → price = Bid
Long Call  = calls closest to shortCall.strike + $5 → price = Ask
```

## UI Flow

```
[Click Rec Card] → setState(ticker) → showLoading → fetchChain(bypass cache) → autoAssembleStrategy → renderLegs + payoffChart
                                                                                    ↓ catch
                                                                           showBreaker(error.message)
```
