# Momentum v3 last run

Overall result: SUCCESS

- Unit tests: success
- Momentum run: success
- Workbook validation: success

## Log tail

```text
test_legacy_v1_rejects_nonpositive_momentum (test_backtest_configuration_v3.BacktestConfigurationTests.test_legacy_v1_rejects_nonpositive_momentum) ... ok
test_legacy_v1_uses_verified_equal_weight_return_score (test_backtest_configuration_v3.BacktestConfigurationTests.test_legacy_v1_uses_verified_equal_weight_return_score) ... ok
test_next_open_falls_back_to_close_when_open_is_unavailable (test_backtest_configuration_v3.BacktestConfigurationTests.test_next_open_falls_back_to_close_when_open_is_unavailable) ... ok
test_next_open_uses_open_and_close_mode_uses_close (test_backtest_configuration_v3.BacktestConfigurationTests.test_next_open_uses_open_and_close_mode_uses_close) ... ok
test_top_n_matches_requested_portfolio_size (test_backtest_configuration_v3.BacktestConfigurationTests.test_top_n_matches_requested_portfolio_size) ... ok
test_top_n_must_be_positive (test_backtest_configuration_v3.BacktestConfigurationTests.test_top_n_must_be_positive) ... ok
test_calendar_rebalances_use_first_session_every_nth_month (test_momentum_master_v3.BacktestTimingTests.test_calendar_rebalances_use_first_session_every_nth_month) ... ok
test_daily_drawdown_holds_stopped_position_as_cash (test_momentum_master_v3.BacktestTimingTests.test_daily_drawdown_holds_stopped_position_as_cash) ... ok
test_execution_is_after_signal_and_exits_at_next_execution (test_momentum_master_v3.BacktestTimingTests.test_execution_is_after_signal_and_exits_at_next_execution) ... ok
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
Ran 27 tests in 0.074s

OK
2026-09-07 20:08:04,113 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 20:08:14,172 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 20:08:34,230 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 20:09:04,288 | WARNING | Polygon rate limit. Waiting 40s and retrying (4/6).
2026-09-07 20:09:44,348 | WARNING | Polygon rate limit. Waiting 50s and retrying (5/6).
2026-09-07 20:10:34,407 | WARNING | Polygon rate limit. Waiting 60s and retrying (6/6).
2026-09-07 20:11:34,407 | INFO | Grouped date 2026-09-06 unavailable: Polygon request failed
2026-09-07 20:11:34,465 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 20:11:44,525 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 20:12:04,648 | INFO | Grouped date 2026-09-05 unavailable: No USDSEK result for 2026-09-05
2026-09-07 20:12:05,267 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-07 20:12:05,949 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 20:12:16,009 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 20:12:36,067 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 20:13:06,437 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 20:13:16,496 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 20:13:36,555 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 20:14:07,270 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-07 20:14:08,842 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 145 candidate rows.

```
