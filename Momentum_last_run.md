# Momentum v3 last run

Overall result: FAILED

- Unit tests: failure
- Momentum run: skipped
- Workbook validation: skipped

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
test_next_open_normalizes_verified_split_mismatch (test_momentum_master_v3.BacktestTimingTests.test_next_open_normalizes_verified_split_mismatch) ... WARNING:root:Normalized split-like open 17.3300 to 86.6500 on 2026-08-04
WARNING:root:Normalized split-like open 17.3300 to 86.6500 on 2026-08-05
WARNING:root:Normalized split-like open 17.3300 to 86.6500 on None
FAIL
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

======================================================================
FAIL: test_next_open_normalizes_verified_split_mismatch (test_momentum_master_v3.BacktestTimingTests.test_next_open_normalizes_verified_split_mismatch)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/runner/work/MomentumCloud/MomentumCloud/tests/test_momentum_master_v3.py", line 103, in test_next_open_normalizes_verified_split_mismatch
    self.assertAlmostEqual(
AssertionError: 19.39 != 77.56 within 8 places (58.17 difference)

----------------------------------------------------------------------
Ran 32 tests in 0.061s

FAILED (failures=1)

```
