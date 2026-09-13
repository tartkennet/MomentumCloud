import unittest
from types import SimpleNamespace

from backtest_momentum_v3 import (
    build_prior_2_12_metrics,
    market_regime_is_risk_on,
    required_adv20_usd,
)


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
    def test_liquidity_gate_scales_from_five_million_floor(self):
        self.assertEqual(required_adv20_usd(10_000, 15), 5_000_000.0)
        self.assertEqual(required_adv20_usd(30_000_000, 15), 2_000_000_000.0)

    def test_research_models_accept_candidate_above_five_million_adv(self):
        closes = [125.0 - 25.0 * index / 252.0 for index in range(253)]
        recent = history_for({"SMALL": closes})
        for _, grouped in recent:
            grouped["SMALL"]["volume"] = 48_000.0
        latest = {"SMALL": {"close": 125.0, "volume": 48_000.0}}

        for model in ("classic-12-2", "v4-balanced"):
            metrics = build_prior_2_12_metrics(
                ["SMALL"], latest, recent, model, min_adv20_usd=5_000_000.0
            )
            self.assertEqual([item.ticker for item in metrics], ["SMALL"])

    def test_research_models_reject_candidate_below_five_million_adv(self):
        closes = [125.0 - 25.0 * index / 252.0 for index in range(253)]
        recent = history_for({"THIN": closes})
        for _, grouped in recent:
            grouped["THIN"]["volume"] = 1_000.0
        latest = {"THIN": {"close": 125.0, "volume": 1_000.0}}

        for model in ("classic-12-2", "v4-balanced"):
            metrics = build_prior_2_12_metrics(
                ["THIN"], latest, recent, model, min_adv20_usd=5_000_000.0
            )
            self.assertEqual(metrics, [])

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

    def test_regime_requires_spy_above_rising_sma200(self):
        rising = [120.0 - 20.0 * index / 252.0 for index in range(253)]
        falling = [80.0 + 20.0 * index / 252.0 for index in range(253)]
        self.assertTrue(
            market_regime_is_risk_on(
                {"SPY": {"close": 120.0}}, history_for({"SPY": rising})
            )
        )
        self.assertFalse(
            market_regime_is_risk_on(
                {"SPY": {"close": 80.0}}, history_for({"SPY": falling})
            )
        )


if __name__ == "__main__":
    unittest.main()
