# Momentum v3 last run

Overall result: SUCCESS

- Unit tests: success
- Momentum run: success
- Workbook validation: success

## Log tail

```text
test_cash_merger_settles_when_no_later_market_price_exists (test_backtest_configuration_v3.BacktestConfigurationTests.test_cash_merger_settles_when_no_later_market_price_exists) ... ok
test_legacy_v1_rejects_nonpositive_momentum (test_backtest_configuration_v3.BacktestConfigurationTests.test_legacy_v1_rejects_nonpositive_momentum) ... ok
test_legacy_v1_uses_verified_equal_weight_return_score (test_backtest_configuration_v3.BacktestConfigurationTests.test_legacy_v1_uses_verified_equal_weight_return_score) ... ok
test_missing_execution_day_moves_to_first_tradable_session (test_backtest_configuration_v3.BacktestConfigurationTests.test_missing_execution_day_moves_to_first_tradable_session) ... ok
test_missing_execution_reports_none_after_latest_allowed_day (test_backtest_configuration_v3.BacktestConfigurationTests.test_missing_execution_reports_none_after_latest_allowed_day) ... ok
test_next_open_falls_back_to_close_when_open_is_unavailable (test_backtest_configuration_v3.BacktestConfigurationTests.test_next_open_falls_back_to_close_when_open_is_unavailable) ... ok
test_next_open_uses_open_and_close_mode_uses_close (test_backtest_configuration_v3.BacktestConfigurationTests.test_next_open_uses_open_and_close_mode_uses_close) ... ok
test_top_n_matches_requested_portfolio_size (test_backtest_configuration_v3.BacktestConfigurationTests.test_top_n_matches_requested_portfolio_size) ... ok
test_top_n_must_be_positive (test_backtest_configuration_v3.BacktestConfigurationTests.test_top_n_must_be_positive) ... ok
test_tradable_exit_before_cash_merger_keeps_market_price (test_backtest_configuration_v3.BacktestConfigurationTests.test_tradable_exit_before_cash_merger_keeps_market_price) ... ok
test_calendar_rebalances_use_first_session_every_nth_month (test_momentum_master_v3.BacktestTimingTests.test_calendar_rebalances_use_first_session_every_nth_month) ... ok
test_daily_drawdown_holds_stopped_position_as_cash (test_momentum_master_v3.BacktestTimingTests.test_daily_drawdown_holds_stopped_position_as_cash) ... ok
test_execution_is_after_signal_and_exits_at_next_execution (test_momentum_master_v3.BacktestTimingTests.test_execution_is_after_signal_and_exits_at_next_execution) ... ok
test_next_open_normalizes_verified_split_mismatch (test_momentum_master_v3.BacktestTimingTests.test_next_open_normalizes_verified_split_mismatch) ... WARNING:root:Normalized split-mismatched open 17.3300 to 86.6500 on 2026-08-04
ok
test_rebalance_point_drawdown (test_momentum_master_v3.BacktestTimingTests.test_rebalance_point_drawdown) ... ok
test_sma50_exit_is_executed_next_session (test_momentum_master_v3.BacktestTimingTests.test_sma50_exit_is_executed_next_session) ... ok
test_stop_loss_is_measured_from_actual_next_open_entry (test_momentum_master_v3.BacktestTimingTests.test_stop_loss_is_measured_from_actual_next_open_entry) ... ok
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
test_max_drawdown_uses_compounded_period_equity (test_walkforward_report_v3.WalkForwardReportTests.test_max_drawdown_uses_compounded_period_equity) ... ok
test_misaligned_periods_are_rejected (test_walkforward_report_v3.WalkForwardReportTests.test_misaligned_periods_are_rejected) ... ok
test_report_is_out_of_sample_and_never_production_eligible (test_walkforward_report_v3.WalkForwardReportTests.test_report_is_out_of_sample_and_never_production_eligible) ... ok
test_selection_does_not_inspect_test_period (test_walkforward_report_v3.WalkForwardReportTests.test_selection_does_not_inspect_test_period) ... ok

----------------------------------------------------------------------
Ran 32 tests in 0.073s

OK
2026-09-08 19:43:46,455 | INFO | Grouped date 2026-09-05 unavailable: No USDSEK result for 2026-09-05
2026-09-08 19:43:46,825 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-08 19:43:47,329 | WARNING | Polygon rate limit. Waiting 45s and retrying (1/12).
2026-09-08 19:44:32,352 | WARNING | Polygon rate limit. Waiting 45s and retrying (2/12).
2026-09-08 19:45:17,369 | WARNING | Polygon rate limit. Waiting 45s and retrying (3/12).
2026-09-08 19:46:02,626 | WARNING | Polygon rate limit. Waiting 45s and retrying (1/12).
2026-09-08 19:46:47,638 | WARNING | Polygon rate limit. Waiting 45s and retrying (2/12).
2026-09-08 19:47:32,650 | WARNING | Polygon rate limit. Waiting 45s and retrying (3/12).
2026-09-08 19:48:17,671 | WARNING | Polygon rate limit. Waiting 45s and retrying (4/12).
2026-09-08 19:49:02,697 | WARNING | Polygon rate limit. Waiting 45s and retrying (5/12).
2026-09-08 19:49:47,710 | WARNING | Polygon rate limit. Waiting 45s and retrying (6/12).
2026-09-08 19:50:32,730 | WARNING | Polygon rate limit. Waiting 45s and retrying (7/12).
2026-09-08 19:51:17,744 | WARNING | Polygon rate limit. Waiting 45s and retrying (8/12).
2026-09-08 19:52:02,757 | WARNING | Polygon rate limit. Waiting 45s and retrying (9/12).
2026-09-08 19:52:47,770 | WARNING | Polygon rate limit. Waiting 45s and retrying (10/12).
2026-09-08 19:53:32,804 | WARNING | Polygon rate limit. Waiting 45s and retrying (11/12).
2026-09-08 19:54:18,538 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-08 19:54:20,063 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 145 candidate rows.

```
