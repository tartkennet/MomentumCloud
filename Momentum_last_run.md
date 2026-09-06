# Momentum v3 last run

Overall result: SUCCESS

- Unit tests: success
- Momentum run: success
- Workbook validation: success

## Log tail

```text
test_calendar_rebalances_use_first_session_every_nth_month (test_momentum_master_v3.BacktestTimingTests.test_calendar_rebalances_use_first_session_every_nth_month) ... ok
test_daily_drawdown_holds_stopped_position_as_cash (test_momentum_master_v3.BacktestTimingTests.test_daily_drawdown_holds_stopped_position_as_cash) ... ok
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
Ran 13 tests in 0.017s

OK
2026-09-06 20:33:18,972 | INFO | Grouped date 2026-09-05 unavailable: No USDSEK result for 2026-09-05
2026-09-06 20:33:19,736 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-06 20:33:20,446 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-06 20:33:30,516 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-06 20:33:50,585 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-06 20:34:21,021 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-06 20:34:31,091 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-06 20:34:51,161 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-06 20:35:21,873 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-06 20:35:23,433 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 145 candidate rows.

```
