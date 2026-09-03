# Momentum v3 last run

Overall result: FAILED

- Unit tests: failure
- Momentum run: skipped
- Workbook validation: skipped

## Log tail

```text
test_buy_history_tracks_entry_and_current_return (test_momentum_master_v3.SimpleMovingAverageTests.test_buy_history_tracks_entry_and_current_return) ... FAIL
test_history_cache_round_trip (test_momentum_master_v3.SimpleMovingAverageTests.test_history_cache_round_trip) ... ok
test_requires_enough_history (test_momentum_master_v3.SimpleMovingAverageTests.test_requires_enough_history) ... ok
test_uses_latest_trading_sessions (test_momentum_master_v3.SimpleMovingAverageTests.test_uses_latest_trading_sessions) ... ok

======================================================================
FAIL: test_buy_history_tracks_entry_and_current_return (test_momentum_master_v3.SimpleMovingAverageTests.test_buy_history_tracks_entry_and_current_return)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/runner/work/MomentumCloud/MomentumCloud/tests/test_momentum_master_v3.py", line 38, in test_buy_history_tracks_entry_and_current_return
    self.assertEqual(second.loc[0, "Return_Since_Entry_pct"], 10.0)
AssertionError: np.float64(10.000000000000009) != 10.0

----------------------------------------------------------------------
Ran 4 tests in 0.012s

FAILED (failures=1)

```
