import unittest
from types import SimpleNamespace

from backtest_momentum_v3 import build_prior_2_12_metrics


def history_for(series_by_ticker):
    rows = []
    for index in range(253):
        grouped = {}
        for ticker, closes in series_by_ticker.items():
            grouped[ticker] = {
                "open": closes[index],
                "high": closes[index],
                "low": closes[index],
                "close": closes[index],
                "volume": 10_000_000.0,
            }
        rows.append((f"session-{index:03d}", grouped))
    return rows


class LockedMomentumSelectionTests(unittest.TestCase):
    def test_classic_12_2_excludes_latest_month_from_score(self):
        formation = [120.0 - 20.0 * index / 231.0 for index in range(232)]
        a = [130.0] * 21 + formation
        b = [240.0] * 21 + formation
        recent = history_for({"A": a, "B": b})
        latest = {
            "A": {"close": 130.0, "volume": 10_000_000.0},
            "B": {"close": 240.0, "volume": 10_000_000.0},
        }

        metrics = build_prior_2_12_metrics(
            ["A", "B"], latest, recent, "classic-12-2"
        )

        scores = {item.ticker: item.total_score for item in metrics}
        self.assertAlmostEqual(scores["A"], scores["B"], places=10)
        self.assertAlmostEqual(scores["A"], 20.0, places=10)

    def test_balanced_model_penalizes_short_term_overextension(self):
        base = [120.0 - 20.0 * index / 231.0 for index in range(232)]
        steady = [125.0 - 5.0 * index / 20.0 for index in range(21)] + base
        extended = [200.0 - 80.0 * index / 20.0 for index in range(21)] + base
        recent = history_for({"STEADY": steady, "EXTENDED": extended})
        latest = {
            "STEADY": {"close": 125.0, "volume": 10_000_000.0},
            "EXTENDED": {"close": 200.0, "volume": 10_000_000.0},
        }

        metrics = build_prior_2_12_metrics(
            ["STEADY", "EXTENDED"], latest, recent, "v4-balanced"
        )

        scores = {item.ticker: item.total_score for item in metrics}
        self.assertGreater(scores["STEADY"], scores["EXTENDED"])


if __name__ == "__main__":
    unittest.main()
