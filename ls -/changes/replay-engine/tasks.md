## 1. Test Fixture (`replay/fixtures/covid_crash_2020.json`)

- [x] 1.1 Slice 1: VIX=45, RSI=30 (Initial Panic, Feb 28 2020)
- [x] 1.2 Slice 2: VIX=82.69, RSI=15 (Peak Panic, Mar 16 2020)
- [x] 1.3 Slice 3: Network Blackout (empty chain, no cash)
- [x] 1.4 Historical prices aligned with real SPY data
- [x] 1.5 _meta blocks with expected_action + expected_reason

## 2. Replay Runner (`replay/runner.py`)

- [x] 2.1 `MockBrokerAdapter` — records orders, no network
- [x] 2.2 `AuditLog` — records KillSwitch events in-memory
- [x] 2.3 ANSI colored terminal output (green/red/cyan/yellow)
- [x] 2.4 `load_fixture()` — JSON array loader
- [x] 2.5 CLI via `argparse` (--fixture flag)
- [x] 2.6 `sys.exit(0)` / `sys.exit(1)` CI-friendly exit codes

## 3. Time-Travel Loop

- [x] 3.1 Constructs StrategyMarketContext per slice
- [x] 3.2 Parses OptionContract chain from JSON
- [x] 3.3 Calls evaluate_market_entry() (strategy engine)

## 4. Assertion Framework

- [x] 4.1 Assert strategy output matches expected_action
- [x] 4.2 Assert VIX > 35 → HOLD (circuit breaker)
- [x] 4.3 Assert VIX > 50 → KillSwitch triggered + Audit Log
- [x] 4.4 Assert zero rogue orders to mock broker
- [x] 4.5 Summary report with pass/fail counts + duration

## 5. CI Validation

- [x] 5.1 `python3 -m replay.runner` → 9/9 PASSED, exit(0) ✅
