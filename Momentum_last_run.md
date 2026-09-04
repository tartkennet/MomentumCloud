# Momentum v3 last run

Overall result: FAILED

- Unit tests: success
- Momentum run: cancelled
- Workbook validation: skipped

## Log tail

```text
test_buy_history_tracks_entry_and_current_return (test_momentum_master_v3.SimpleMovingAverageTests.test_buy_history_tracks_entry_and_current_return) ... ok
test_history_cache_round_trip (test_momentum_master_v3.SimpleMovingAverageTests.test_history_cache_round_trip) ... ok
test_holdings_compare_to_spy_and_current_rank (test_momentum_master_v3.SimpleMovingAverageTests.test_holdings_compare_to_spy_and_current_rank) ... ok
test_requires_enough_history (test_momentum_master_v3.SimpleMovingAverageTests.test_requires_enough_history) ... ok
test_uses_latest_trading_sessions (test_momentum_master_v3.SimpleMovingAverageTests.test_uses_latest_trading_sessions) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.010s

OK
2026-09-04 21:17:02,692 | INFO | Using grouped stock date 2026-09-03 with 12507 symbols, USDSEK 9.5339
2026-09-04 21:17:03,083 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-04 21:17:13,094 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).

```
