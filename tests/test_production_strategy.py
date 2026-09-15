import unittest

from momentum_config import PRODUCTION
from momentum_strategy import (
    Security,
    build_target_portfolio,
    is_eligible_security,
    market_regime,
    rank_universe,
    stop_is_triggered,
)


def history_for(series_by_ticker, volumes=None):
    rows = []
    for index in range(253):
        grouped = {}
        for ticker, closes in series_by_ticker.items():
            grouped[ticker] = {
                "open": closes[index],
                "high": closes[index],
                "low": closes[index],
                "close": closes[index],
                "volume": (volumes or {}).get(ticker, 1_000_000.0),
            }
        rows.append((f"session-{index:03d}", grouped))
    return rows


class ProductionConfigTests(unittest.TestCase):
    def test_locked_configuration(self):
        self.assertEqual(PRODUCTION.selection_model, "v4-balanced")
        self.assertEqual(PRODUCTION.position_count, 15)
        self.assertEqual(PRODUCTION.candidate_count, 50)
        self.assertEqual(PRODUCTION.min_price_usd, 10.0)
        self.assertEqual(PRODUCTION.min_adv20_usd, 5_000_000.0)
        self.assertEqual(PRODUCTION.stop_loss_pct, 10.0)
        self.assertAlmostEqual(
            PRODUCTION.weight_rank_12_2
            + PRODUCTION.weight_rank_6_2
            + PRODUCTION.weight_low_volatility
            + PRODUCTION.weight_low_extension,
            1.0,
        )
        self.assertEqual(PRODUCTION.limitation, "Current limitation: survivorship bias")

    def test_instrument_filter_is_fail_closed(self):
        self.assertTrue(is_eligible_security(Security("GOOD", "Good Inc", "CS", "XNAS")))
        self.assertFalse(is_eligible_security(Security("ETF", "Fund", "ETF", "XNAS")))
        self.assertFalse(is_eligible_security(Security("ADR", "Issuer ADR", "ADRC", "XNYS")))
        self.assertFalse(is_eligible_security(Security("PREF", "Preferred", "PFD", "XNYS")))
        self.assertFalse(is_eligible_security(Security("SPAC", "Alpha Acquisition Corp", "CS", "XNAS")))
        self.assertFalse(is_eligible_security(Security("OTC", "OTC Inc", "CS", "PINX")))

    def test_exact_five_million_liquidity_and_ten_dollar_price(self):
        rising = [130.0 - 30.0 * index / 252.0 for index in range(253)]
        recent = history_for(
            {"PASS": rising, "THIN": rising, "CHEAP": [9.0 - index / 1000 for index in range(253)]},
            {"PASS": 40_000.0, "THIN": 30_000.0, "CHEAP": 1_000_000.0},
        )
        ranked = rank_universe(["PASS", "THIN", "CHEAP"], recent)
        self.assertEqual([row.ticker for row in ranked], ["PASS"])

    def test_balanced_score_rewards_lower_volatility_and_extension(self):
        base = [120.0 - 20.0 * index / 231.0 for index in range(232)]
        steady = [125.0 - 5.0 * index / 20.0 for index in range(21)] + base
        extended = [200.0 - 80.0 * index / 20.0 for index in range(21)] + base
        ranked = rank_universe(["STEADY", "EXTENDED"], history_for({"STEADY": steady, "EXTENDED": extended}))
        self.assertEqual(ranked[0].ticker, "STEADY")
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_split_sized_adjusted_price_discontinuity_is_rejected(self):
        clean = [130.0 - 30.0 * index / 252.0 for index in range(253)]
        broken = list(clean)
        broken[100] = broken[99] / 4.0
        ranked = rank_universe(
            ["CLEAN", "BROKEN"],
            history_for({"CLEAN": clean, "BROKEN": broken}),
        )
        self.assertEqual([row.ticker for row in ranked], ["CLEAN"])

    def test_spy_regime_is_exactly_price_above_sma200(self):
        flat = [100.0] * 253
        risk_on = history_for({"SPY": flat})
        risk_on[0][1]["SPY"]["close"] = 101.0
        self.assertEqual(market_regime(risk_on)["status"], "RISK ON")
        self.assertEqual(market_regime(history_for({"SPY": flat}))["status"], "RISK OFF")

    def test_risk_off_has_no_target_and_risk_on_has_15_equal_weights(self):
        from momentum_strategy import MomentumMetric
        metrics = [
            MomentumMetric(str(index), 20, 6_000_000, 18, 15, 14, 20, 10, 25, 5, 90-index)
            for index in range(20)
        ]
        self.assertEqual(build_target_portfolio(metrics, False), [])
        target = build_target_portfolio(metrics, True)
        self.assertEqual(len(target), 15)
        self.assertTrue(all(abs(row["weight_pct"] - 100 / 15) < 1e-10 for row in target))

    def test_target_skips_shares_that_are_not_affordable(self):
        from momentum_strategy import MomentumMetric
        metrics = [
            MomentumMetric("EXPENSIVE", 1_000, 6_000_000, 900, 800, 700, 20, 10, 25, 5, 100),
            *[
                MomentumMetric(str(index), 20, 6_000_000, 18, 15, 14, 20, 10, 25, 5, 90-index)
                for index in range(20)
            ],
        ]
        target = build_target_portfolio(
            metrics,
            True,
            portfolio_value_sek=15_000,
            usdsek=10,
        )
        self.assertEqual(len(target), 15)
        self.assertNotIn("EXPENSIVE", {row["ticker"] for row in target})
        self.assertTrue(all(row["quantity"] >= 1 for row in target))
        self.assertEqual([row["target_rank"] for row in target], list(range(1, 16)))

    def test_stop_loss_is_locked_to_ten_percent(self):
        self.assertFalse(stop_is_triggered(90.01, 100.0))
        self.assertTrue(stop_is_triggered(90.0, 100.0))


if __name__ == "__main__":
    unittest.main()
