# Momentum v3 last run

Overall result: FAILED

- Unit tests: success
- Momentum run: cancelled
- Workbook validation: skipped

## Log tail

```text
test_calendar_rebalances_use_first_session_every_nth_month (test_momentum_master_v3.BacktestTimingTests.test_calendar_rebalances_use_first_session_every_nth_month) ... ok
test_execution_is_after_signal_and_exits_at_next_execution (test_momentum_master_v3.BacktestTimingTests.test_execution_is_after_signal_and_exits_at_next_execution) ... ok
test_rebalance_point_drawdown (test_momentum_master_v3.BacktestTimingTests.test_rebalance_point_drawdown) ... ok
test_sma50_exit_is_executed_next_session (test_momentum_master_v3.BacktestTimingTests.test_sma50_exit_is_executed_next_session) ... ok
test_stop_loss_signals_at_close_and_exits_next_session (test_momentum_master_v3.BacktestTimingTests.test_stop_loss_signals_at_close_and_exits_next_session) ... ok
test_buy_history_tracks_entry_and_current_return (test_momentum_master_v3.SimpleMovingAverageTests.test_buy_history_tracks_entry_and_current_return) ... ok
test_history_cache_round_trip (test_momentum_master_v3.SimpleMovingAverageTests.test_history_cache_round_trip) ... ok
test_holdings_compare_to_spy_and_current_rank (test_momentum_master_v3.SimpleMovingAverageTests.test_holdings_compare_to_spy_and_current_rank) ... ok
test_requires_enough_history (test_momentum_master_v3.SimpleMovingAverageTests.test_requires_enough_history) ... ok
test_return_columns_get_positive_negative_formatting (test_momentum_master_v3.SimpleMovingAverageTests.test_return_columns_get_positive_negative_formatting) ... ok
test_split_price_factor_normalizes_entry_price (test_momentum_master_v3.SimpleMovingAverageTests.test_split_price_factor_normalizes_entry_price) ... ok
test_uses_latest_trading_sessions (test_momentum_master_v3.SimpleMovingAverageTests.test_uses_latest_trading_sessions) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.014s

OK
2026-09-06 20:31:18,654 | INFO | Grouped date 2026-09-05 unavailable: No USDSEK result for 2026-09-05
2026-09-06 20:31:18,963 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-06 20:31:19,434 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-06 20:31:29,447 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-06 20:31:49,460 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-06 20:32:19,553 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-06 20:32:29,566 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).

```
