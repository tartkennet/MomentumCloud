"""Verify that v3 really removes the strict gates without losing causal inputs."""
from datetime import date, timedelta
import unittest

import numpy as np

import momentum_selection_v3 as broad
import risk_managed_momentum as strict


def inputs(series):
    start = date(2024, 1, 1)
    chronological = [(str(start + timedelta(days=i)),
                      {ticker: {"close": float(values[i])} for ticker, values in series.items()})
                     for i in range(253)]
    history = chronological[::-1]
    raw = {ticker: 30.0 for ticker in series}
    dollars = {day: {ticker: 50e6 for ticker in series} for day, _ in history}
    return history, raw, dollars


class BroadSelectionTests(unittest.TestCase):
    def test_negative_momentum_and_declining_trend_are_rankable(self):
        t = np.arange(253)
        h, raw, dollars = inputs({"DECLINING": 100 * np.exp(-.001*t + .003*np.sin(t))})
        rankings, rejected = broad.rank_candidates(["DECLINING"], h, h[0][0], raw, dollars)
        self.assertEqual(rejected, {})
        for values in rankings.values():
            self.assertEqual(len(values), 1)
            self.assertLess(values[0].mom12_1, 0)
        old, counts = strict.rank_candidates(["DECLINING"], h, h[0][0], raw, dollars)
        self.assertEqual(old, [])
        self.assertEqual(counts, {"trend_or_momentum": 1})

    def test_high_volatility_jump_and_extension_are_not_hard_exclusions(self):
        t = np.arange(253)
        prices = 100 * np.exp(.002*t + .003*np.sin(t))
        prices[-20:] *= 4
        h, raw, dollars = inputs({"VOLATILE": prices})
        rankings, rejected = broad.rank_candidates(["VOLATILE"], h, h[0][0], raw, dollars)
        self.assertEqual(rejected, {})
        candidate = rankings["broad_momentum"][0]
        self.assertGreater(candidate.vol63, .6)
        self.assertGreater(candidate.max_abs_daily63, .25)
        self.assertGreater(candidate.extension50, .25)
        self.assertEqual(len(rankings["broad_risk_adjusted"]), 1)
        self.assertEqual(strict.rank_candidates(["VOLATILE"], h, h[0][0], raw, dollars)[0], [])

    def test_soft_risk_ranking_changes_preference_not_eligibility(self):
        t = np.arange(253)
        h, raw, dollars = inputs({"FAST": 100*np.exp(.003*t + .2*np.sin(t)),
                                  "STEADY": 100*np.exp(.001*t + .002*np.sin(t))})
        ranked, _ = broad.rank_candidates(raw, h, h[0][0], raw, dollars)
        self.assertEqual([c.ticker for c in ranked["broad_momentum"]], ["FAST", "STEADY"])
        self.assertEqual([c.ticker for c in ranked["broad_risk_adjusted"]], ["STEADY", "FAST"])

    def test_last_month_changes_risk_but_not_completed_momentum(self):
        t = np.arange(253)
        h, raw, dollars = inputs({"AAA": 100*np.exp(.001*t + .003*np.sin(t))})
        original = broad.rank_candidates(raw, h, h[0][0], raw, dollars)[0]["broad_momentum"][0]
        for i in range(21):
            h[i][1]["AAA"]["close"] *= 2
        updated = broad.rank_candidates(raw, h, h[0][0], raw, dollars)[0]["broad_momentum"][0]
        self.assertEqual((original.mom12_1, original.mom6_1, original.mom3_1),
                         (updated.mom12_1, updated.mom6_1, updated.mom3_1))
        self.assertNotEqual(original.vol63, updated.vol63)

    def test_looser_raw_tradeability_thresholds_are_exact(self):
        t = np.arange(253)
        h, raw, dollars = inputs({"AAA": 100*np.exp(.001*t + .003*np.sin(t))})
        raw["AAA"] = 5
        for values in dollars.values(): values["AAA"] = 2e6
        self.assertEqual(len(broad.rank_candidates(raw, h, h[0][0], raw, dollars)[0]["broad_momentum"]), 1)
        raw["AAA"] = 4.99
        self.assertEqual(broad.rank_candidates(raw, h, h[0][0], raw, dollars)[1], {"raw_price_floor": 1})
        raw["AAA"] = 5
        dollars[h[7][0]]["AAA"] = None
        self.assertEqual(broad.rank_candidates(raw, h, h[0][0], raw, dollars)[1], {"missing_raw_adv20": 1})

    def test_missing_invalid_and_future_history_cannot_create_a_choice(self):
        t = np.arange(253)
        h, raw, dollars = inputs({"AAA": 100*np.exp(.001*t + .003*np.sin(t))})
        with self.assertRaises(ValueError):
            broad.rank_candidates(raw, h, h[1][0], raw, dollars)
        with self.assertRaises(ValueError):
            broad.rank_candidates(raw, h[:252], h[0][0], raw, dollars)
        h[100][1]["AAA"]["close"] = float("nan")
        self.assertEqual(broad.rank_candidates(raw, h, h[0][0], raw, dollars)[1], {"invalid_formation": 1})

    def test_flat_risk_estimate_is_undefined_for_unchanged_sizing(self):
        h, raw, dollars = inputs({"AAA": np.full(253, 100.)})
        rankings, counts = broad.rank_candidates(["AAA", "AAA"], h, h[0][0], raw, dollars)
        self.assertTrue(all(not values for values in rankings.values()))
        self.assertEqual(counts, {"undefined_risk_or_momentum": 1})


if __name__ == "__main__":
    unittest.main()
