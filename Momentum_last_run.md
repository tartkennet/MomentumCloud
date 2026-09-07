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
test_max_drawdown_uses_compounded_period_equity (test_walkforward_report_v3.WalkForwardReportTests.test_max_drawdown_uses_compounded_period_equity) ... ok
test_misaligned_periods_are_rejected (test_walkforward_report_v3.WalkForwardReportTests.test_misaligned_periods_are_rejected) ... ok
test_report_is_out_of_sample_and_never_production_eligible (test_walkforward_report_v3.WalkForwardReportTests.test_report_is_out_of_sample_and_never_production_eligible) ... ok
test_selection_does_not_inspect_test_period (test_walkforward_report_v3.WalkForwardReportTests.test_selection_does_not_inspect_test_period) ... ok

----------------------------------------------------------------------
Ran 20 tests in 0.048s

OK
2026-09-07 19:10:16,091 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 19:10:26,151 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 19:10:46,210 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 19:11:16,271 | WARNING | Polygon rate limit. Waiting 40s and retrying (4/6).
2026-09-07 19:11:56,331 | WARNING | Polygon rate limit. Waiting 50s and retrying (5/6).
2026-09-07 19:12:46,391 | WARNING | Polygon rate limit. Waiting 60s and retrying (6/6).
2026-09-07 19:13:46,392 | INFO | Grouped date 2026-09-06 unavailable: Polygon request failed
2026-09-07 19:13:46,451 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 19:13:56,511 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 19:14:16,638 | INFO | Grouped date 2026-09-05 unavailable: No USDSEK result for 2026-09-05
2026-09-07 19:14:17,304 | INFO | Using grouped stock date 2026-09-04 with 12508 symbols, USDSEK 9.5651
2026-09-07 19:14:17,926 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 19:14:27,984 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 19:14:48,044 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 19:15:18,103 | WARNING | Polygon rate limit. Waiting 40s and retrying (4/6).
2026-09-07 19:15:58,163 | WARNING | Polygon rate limit. Waiting 50s and retrying (5/6).
2026-09-07 19:16:48,222 | WARNING | Polygon rate limit. Waiting 60s and retrying (6/6).
2026-09-07 19:17:48,282 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 19:17:58,341 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 19:18:18,401 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 19:18:48,461 | WARNING | Polygon rate limit. Waiting 40s and retrying (4/6).
2026-09-07 19:19:28,520 | WARNING | Polygon rate limit. Waiting 50s and retrying (5/6).
2026-09-07 19:20:18,579 | WARNING | Polygon rate limit. Waiting 60s and retrying (6/6).
2026-09-07 19:21:18,638 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 19:21:28,701 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 19:21:48,760 | WARNING | Polygon rate limit. Waiting 30s and retrying (3/6).
2026-09-07 19:22:18,819 | WARNING | Polygon rate limit. Waiting 40s and retrying (4/6).
2026-09-07 19:22:58,879 | WARNING | Polygon rate limit. Waiting 50s and retrying (5/6).
2026-09-07 19:23:48,940 | WARNING | Polygon rate limit. Waiting 60s and retrying (6/6).
2026-09-07 19:24:48,999 | WARNING | Polygon rate limit. Waiting 10s and retrying (1/6).
2026-09-07 19:24:59,059 | WARNING | Polygon rate limit. Waiting 20s and retrying (2/6).
2026-09-07 19:25:20,134 | INFO | Loaded 253 recent trading sessions for returns and real SMA calculations.
2026-09-07 19:25:21,621 | INFO | Wrote Momentum.xlsx with 15 BuyNow rows and 145 candidate rows.

```
