import tempfile
import unittest
from pathlib import Path

import pandas as pd

from robustness_report_v3 import compounded_return, rolling_windows, build_report


class RobustnessReportTests(unittest.TestCase):
    def test_compounds_returns(self):
        self.assertAlmostEqual(compounded_return(pd.Series([10.0, -10.0])), -1.0)

    def test_rolling_window_has_no_forward_periods(self):
        results = pd.DataFrame(
            [
                {"EntryDate": "2026-01-02", "ExitDate": "2026-02-02", "NetReturn_pct": 1, "SPYReturn_pct": 0},
                {"EntryDate": "2026-02-02", "ExitDate": "2026-03-02", "NetReturn_pct": 2, "SPYReturn_pct": 1},
                {"EntryDate": "2026-03-02", "ExitDate": "2026-04-01", "NetReturn_pct": 3, "SPYReturn_pct": 1},
                {"EntryDate": "2026-04-02", "ExitDate": "2026-05-01", "NetReturn_pct": 99, "SPYReturn_pct": 0},
            ]
        )
        windows = rolling_windows(results, "test", 3)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["EndExitDate"], "2026-04-01")
        self.assertAlmostEqual(windows[0]["NetReturn_pct"], 6.1106, places=4)

    def test_build_report_marks_current_universe_as_not_production_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = "Momentum_robustness"
            pd.DataFrame([{
                "Periods": 3, "TotalReturn_pct": 5, "SPYTotalReturn_pct": 3,
                "TotalEdgeVsSPY_pct": 2, "PeriodHitRate_pct": 66.7,
                "BestPeriod_pct": 4, "WorstPeriod_pct": -2,
                "DailyMaxDrawdown_pct": -5, "EarlyExitPositions": 1,
                "Execution": "SIGNAL_CLOSE_ENTRY_NEXT_SESSION",
                "Universe": "CURRENT_TEMPLATE_SURVIVORSHIP_BIAS",
            }]).to_csv(root / f"{prefix}_stop8_summary.csv", index=False)
            pd.DataFrame([
                {"EntryDate": "2026-01-02", "ExitDate": "2026-02-02", "NetReturn_pct": 1, "SPYReturn_pct": 0},
                {"EntryDate": "2026-02-02", "ExitDate": "2026-03-02", "NetReturn_pct": 2, "SPYReturn_pct": 1},
                {"EntryDate": "2026-03-02", "ExitDate": "2026-04-01", "NetReturn_pct": 2, "SPYReturn_pct": 2},
            ]).to_csv(root / f"{prefix}_stop8_results.csv", index=False)
            pd.DataFrame([
                {"Ticker": "ABC", "GrossReturn_pct": 3},
                {"Ticker": "XYZ", "GrossReturn_pct": -7},
            ]).to_csv(root / f"{prefix}_stop8_positions.csv", index=False)
            comparison, windows = build_report(root, prefix)
            self.assertFalse(bool(comparison.loc[0, "ProductionEligible"]))
            self.assertEqual(comparison.loc[0, "WorstPositionTicker"], "XYZ")
            self.assertEqual(len(windows), 1)


if __name__ == "__main__":
    unittest.main()
