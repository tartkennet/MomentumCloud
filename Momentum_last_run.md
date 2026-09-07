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
test_build_report_marks_current_universe_as_not_production_eligible (test_robustness_report_v3.RobustnessReportTests.test_build_report_marks_current_universe_as_not_production_eligible) ... ok
test_compounds_returns (test_robustness_report_v3.RobustnessReportTests.test_compounds_returns) ... ok
test_rolling_window_has_no_forward_periods (test_robustness_report_v3.RobustnessReportTests.test_rolling_window_has_no_forward_periods) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.029s

OK
2026-09-07 10:01:11,217 | INFO | Grouped date 2026-09-05 unavailable: No USDSEK result for 2026-09-05
2026-09-07 10:01:11,616 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-07 10:01:12,132 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 10:01:22,155 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 10:01:42,178 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 10:02:12,339 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 10:02:22,362 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 10:02:42,386 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 10:03:13,101 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-07 10:03:14,621 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 145 candidate rows.

```
