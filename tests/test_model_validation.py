import json
import tempfile
import unittest
from pathlib import Path

from model_validation import load_model_validation


class ModelValidationTests(unittest.TestCase):
    def test_missing_decision_is_unvalidated(self):
        with tempfile.TemporaryDirectory() as directory:
            decision = load_model_validation(Path(directory) / "missing.json")
        self.assertFalse(decision["approved"])
        self.assertEqual(decision["status"], "UNVALIDATED")

    def test_only_complete_point_in_time_go_is_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decision.json"
            path.write_text(json.dumps({
                "model": "relative-strength-breakout-v1",
                "universe": "POINT_IN_TIME_US_COMMON_STOCKS",
                "status": "GO",
                "gates": {
                    "at_least_30_periods": True,
                    "positive_net_return": True,
                    "beats_spy": True,
                    "daily_max_drawdown_at_most_20_pct": True,
                    "hit_rate_at_least_50_pct": True,
                },
            }), encoding="utf-8")
            decision = load_model_validation(path)
        self.assertTrue(decision["approved"])
        self.assertEqual(decision["status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
