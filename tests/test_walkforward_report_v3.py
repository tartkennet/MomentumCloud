import tempfile
import unittest
from pathlib import Path

import pandas as pd

from walkforward_report_v3 import (
    STOP_VARIANTS,
    build_walkforward_report,
    choose_variant,
    max_drawdown,
)


def frame(returns):
    rows = []
    for index, value in enumerate(returns, start=1):
        rows.append({
            "SignalDate": f"2026-{index:02d}-01",
            "EntryDate": f"2026-{index:02d}-02",
            "ExitDate": f"2026-{index:02d}-28",
            "NetReturn_pct": value,
            "SPYReturn_pct": 1.0,
        })
    return pd.DataFrame(rows)


class WalkForwardReportTests(unittest.TestCase):
    def test_max_drawdown_uses_compounded_period_equity(self):
        self.assertAlmostEqual(max_drawdown(pd.Series([10.0, -20.0, 5.0])), -20.0)

    def test_selection_does_not_inspect_test_period(self):
        frames = {
            "stop6_next_open": frame([1, 2, 1, 2, 1, 2, -99]),
            "stop8_next_open": frame([1, -1, 1, -1, 1, -1, 999]),
            "stop10_next_open": frame([-1, -2, -1, -2, -1, -2, 999]),
            "stop12_next_open": frame([-2, -1, -2, -1, -2, -1, 999]),
        }
        selected, _ = choose_variant(frames, 0, 6)
        self.assertEqual(selected, "stop6_next_open")

    def test_report_is_out_of_sample_and_never_production_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = {
                "stop6_next_open": [1, 2, 1, 2, 1, 2, 3, 4],
                "stop8_next_open": [1, -1, 1, -1, 1, -1, 50, 50],
                "stop10_next_open": [-1] * 8,
                "stop12_next_open": [-2] * 8,
            }
            for variant in STOP_VARIANTS:
                frame(values[variant]).to_csv(
                    root / f"Momentum_walk_forward_{variant}_results.csv", index=False
                )
            decisions, comparison = build_walkforward_report(root, training_periods=6)
            self.assertEqual(len(decisions), 2)
            self.assertEqual(decisions.iloc[0]["SelectedVariant"], "stop6_next_open")
            self.assertEqual(decisions.iloc[0]["OOSNetReturn_pct"], 3)
            self.assertTrue((comparison["ProductionEligible"] == False).all())
            self.assertTrue((comparison["Validation"] == "ROLLING_WALK_FORWARD_NO_LOOKAHEAD").all())
            self.assertTrue((comparison["Universe"] == "CURRENT_TEMPLATE_SURVIVORSHIP_BIAS").all())

    def test_misaligned_periods_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for variant in STOP_VARIANTS:
                data = frame([1] * 7)
                if variant == "stop12_next_open":
                    data.loc[6, "SignalDate"] = "2026-12-31"
                data.to_csv(root / f"Momentum_walk_forward_{variant}_results.csv", index=False)
            with self.assertRaisesRegex(RuntimeError, "identical chronological periods"):
                build_walkforward_report(root, training_periods=6)


if __name__ == "__main__":
    unittest.main()
