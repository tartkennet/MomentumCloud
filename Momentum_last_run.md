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
test_return_columns_get_positive_negative_formatting (test_momentum_master_v3.SimpleMovingAverageTests.test_return_columns_get_positive_negative_formatting) ... ok
test_split_price_factor_normalizes_entry_price (test_momentum_master_v3.SimpleMovingAverageTests.test_split_price_factor_normalizes_entry_price) ... ok
test_uses_latest_trading_sessions (test_momentum_master_v3.SimpleMovingAverageTests.test_uses_latest_trading_sessions) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.021s

OK
2026-09-05 06:49:27,644 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-05 06:49:28,421 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-05 06:49:38,479 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-05 06:49:58,536 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-05 06:50:29,498 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-05 06:50:31,138 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 145 candidate rows.

```
