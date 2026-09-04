# Momentum v3 last run

Overall result: SUCCESS

- Unit tests: success
- Momentum run: success
- Workbook validation: success

## Log tail

```text
test_buy_history_tracks_entry_and_current_return (test_momentum_master_v3.SimpleMovingAverageTests.test_buy_history_tracks_entry_and_current_return) ... ok
test_history_cache_round_trip (test_momentum_master_v3.SimpleMovingAverageTests.test_history_cache_round_trip) ... ok
test_holdings_compare_to_spy_and_current_rank (test_momentum_master_v3.SimpleMovingAverageTests.test_holdings_compare_to_spy_and_current_rank) ... ok
test_requires_enough_history (test_momentum_master_v3.SimpleMovingAverageTests.test_requires_enough_history) ... ok
test_uses_latest_trading_sessions (test_momentum_master_v3.SimpleMovingAverageTests.test_uses_latest_trading_sessions) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.013s

OK
2026-09-04 21:17:48,488 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-04 21:17:58,519 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-04 21:18:18,954 | INFO | Using grouped stock date 2026-09-03 with 12507 symbols, USDSEK 9.5339
2026-09-04 21:18:19,542 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-04 21:18:29,569 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-04 21:18:49,595 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-04 21:19:20,389 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-04 21:19:21,924 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 149 candidate rows.

```
