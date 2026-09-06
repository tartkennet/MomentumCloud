# Momentum v3 last run

Overall result: SUCCESS

- Unit tests: success
- Momentum run: success
- Workbook validation: success

## Log tail

```text
test_calendar_rebalances_use_first_session_every_nth_month (test_momentum_master_v3.BacktestTimingTests.test_calendar_rebalances_use_first_session_every_nth_month) ... ok
test_execution_is_after_signal_and_exits_at_next_execution (test_momentum_master_v3.BacktestTimingTests.test_execution_is_after_signal_and_exits_at_next_execution) ... ok
test_buy_history_tracks_entry_and_current_return (test_momentum_master_v3.SimpleMovingAverageTests.test_buy_history_tracks_entry_and_current_return) ... ok
test_history_cache_round_trip (test_momentum_master_v3.SimpleMovingAverageTests.test_history_cache_round_trip) ... ok
test_holdings_compare_to_spy_and_current_rank (test_momentum_master_v3.SimpleMovingAverageTests.test_holdings_compare_to_spy_and_current_rank) ... ok
test_requires_enough_history (test_momentum_master_v3.SimpleMovingAverageTests.test_requires_enough_history) ... ok
test_return_columns_get_positive_negative_formatting (test_momentum_master_v3.SimpleMovingAverageTests.test_return_columns_get_positive_negative_formatting) ... ok
test_split_price_factor_normalizes_entry_price (test_momentum_master_v3.SimpleMovingAverageTests.test_split_price_factor_normalizes_entry_price) ... ok
test_uses_latest_trading_sessions (test_momentum_master_v3.SimpleMovingAverageTests.test_uses_latest_trading_sessions) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.010s

OK
2026-09-06 10:51:13,376 | INFO | Grouped date 2026-09-05 unavailable: No USDSEK result for 2026-09-05
2026-09-06 10:51:14,070 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-06 10:51:14,750 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-06 10:51:24,819 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-06 10:51:44,886 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-06 10:52:15,304 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-06 10:52:25,372 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-06 10:52:45,438 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-06 10:53:16,085 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-06 10:53:17,131 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 145 candidate rows.

```
