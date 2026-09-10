# Momentum v3 last run

Overall result: FAILED

- Unit tests: success
- Momentum run: cancelled
- Workbook validation: skipped

## Log tail

```text
test_legacy_cache_without_basis_is_rejected (test_backtest_cache_split_basis.BacktestCacheSplitBasisTests.test_legacy_cache_without_basis_is_rejected) ... WARNING:root:Discarding unsafe backtest cache: legacy cache has an unknown split-adjustment basis
ok
test_split_moves_older_rows_to_new_basis_once (test_backtest_cache_split_basis.BacktestCacheSplitBasisTests.test_split_moves_older_rows_to_new_basis_once) ... ok
test_v2_round_trip_preserves_basis (test_backtest_cache_split_basis.BacktestCacheSplitBasisTests.test_v2_round_trip_preserves_basis) ... ok
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
WARNING:root:Normalized split-like open 19.3900 to 77.5600 on None
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
Ran 35 tests in 0.054s

OK
2026-09-10 05:51:27,801 | WARNING | Polygon rate limit. Waiting 45s and retrying (1/12).
2026-09-10 05:52:13,407 | INFO | Using grouped stock date 2026-09-09 with 12518 symbols, USDSEK 9.5895
2026-09-10 05:52:13,793 | WARNING | Polygon rate limit. Waiting 45s and retrying (1/12).
2026-09-10 05:52:58,868 | WARNING | Polygon rate limit. Waiting 45s and retrying (2/12).
2026-09-10 05:53:43,927 | WARNING | Polygon rate limit. Waiting 45s and retrying (3/12).
2026-09-10 05:54:28,987 | WARNING | Polygon rate limit. Waiting 45s and retrying (4/12).
2026-09-10 05:55:14,047 | WARNING | Polygon rate limit. Waiting 45s and retrying (5/12).
2026-09-10 05:55:59,105 | WARNING | Polygon rate limit. Waiting 45s and retrying (6/12).
2026-09-10 05:56:44,165 | WARNING | Polygon rate limit. Waiting 45s and retrying (7/12).
2026-09-10 05:57:29,226 | WARNING | Polygon rate limit. Waiting 45s and retrying (8/12).
2026-09-10 05:58:14,285 | WARNING | Polygon rate limit. Waiting 45s and retrying (9/12).
2026-09-10 05:58:59,344 | WARNING | Polygon rate limit. Waiting 45s and retrying (10/12).
2026-09-10 05:59:44,404 | WARNING | Polygon rate limit. Waiting 45s and retrying (11/12).
2026-09-10 06:00:29,464 | WARNING | Polygon rate limit. Waiting 45s and retrying (12/12).
2026-09-10 06:01:14,526 | WARNING | Polygon rate limit. Waiting 45s and retrying (1/12).
2026-09-10 06:01:59,586 | WARNING | Polygon rate limit. Waiting 45s and retrying (2/12).

```
