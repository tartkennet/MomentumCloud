# Momentum v3 last run

Overall result: SUCCESS

- Unit tests: success
- Momentum run: success
- Workbook validation: success

## Log tail

```text
test_buy_history_tracks_entry_and_current_return (test_momentum_master_v3.SimpleMovingAverageTests.test_buy_history_tracks_entry_and_current_return) ... ok
test_history_cache_round_trip (test_momentum_master_v3.SimpleMovingAverageTests.test_history_cache_round_trip) ... ok
test_requires_enough_history (test_momentum_master_v3.SimpleMovingAverageTests.test_requires_enough_history) ... ok
test_uses_latest_trading_sessions (test_momentum_master_v3.SimpleMovingAverageTests.test_uses_latest_trading_sessions) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.009s

OK
2026-09-03 15:36:59,160 | INFO | Using grouped stock date 2026-09-02 with 12539 symbols, USDSEK 9.6314
2026-09-03 15:36:59,832 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-03 15:37:11,038 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-03 15:37:12,381 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 132 candidate rows.

```
