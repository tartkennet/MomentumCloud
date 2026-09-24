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
    series_by_ticker = dict(series_by_ticker)
    series_by_ticker.setdefault("SPY", [100.0] * 253)
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
        self.assertEqual(PRODUCTION.weight_rank_12_2, 0.55)
        self.assertEqual(PRODUCTION.weight_rank_6_2, 0.20)
        self.assertEqual(PRODUCTION.weight_low_volatility, 0.15)
        self.assertEqual(PRODUCTION.weight_low_extension, 0.10)
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

    def test_fresh_one_and_three_month_strength_drives_score(self):
        steady = [150.0 - 50.0 * index / 252.0 for index in range(253)]
        fresher = [170.0 - 70.0 * index / 252.0 for index in range(253)]
        ranked = rank_universe(
            ["STEADY", "FRESHER"],
            history_for({"STEADY": steady, "FRESHER": fresher}),
        )
        self.assertEqual(ranked[0].ticker, "FRESHER")
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_old_momentum_cannot_hide_negative_one_or_three_month_return(self):
        fresh = [140.0 - 40.0 * index / 252.0 for index in range(253)]
        stale = [100.0 + 5.0 * index / 63.0 for index in range(64)] + [
            105.0 - 25.0 * (index - 63) / 189.0 for index in range(64, 253)
        ]
        ranked = rank_universe(
            ["FRESH", "STALE"],
            history_for({"FRESH": fresh, "STALE": stale}),
        )
        self.assertEqual([row.ticker for row in ranked], ["FRESH"])

    def test_v4_ranking_does_not_require_short_term_relative_spy_return(self):
        laggard = [150.0 - 50.0 * index / 252.0 for index in range(253)]
        leader = [180.0 - 80.0 * index / 252.0 for index in range(253)]
        spy = [160.0 - 60.0 * index / 252.0 for index in range(253)]
        ranked = rank_universe(
            ["LAGGARD", "LEADER"],
            history_for({"LAGGARD": laggard, "LEADER": leader, "SPY": spy}),
        )
        self.assertEqual([row.ticker for row in ranked], ["LEADER", "LAGGARD"])
        self.assertGreater(ranked[0].mom12_2_pct, ranked[1].mom12_2_pct)
        self.assertGreater(ranked[0].mom6_2_pct, ranked[1].mom6_2_pct)

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
        def metric(ticker, score):
            return MomentumMetric(
                ticker=ticker, price_usd=20, adv20_usd=6_000_000,
                sma20=19, sma50=18, sma50_1m_ago=17, sma200=15,
                sma200_1m_ago=14, return_1m_pct=8, return_3m_pct=20,
                return_6m_pct=30, spy_return_1m_pct=2,
                spy_return_3m_pct=5, relative_1m_pct=6,
                relative_3m_pct=15, volatility_pct=25,
                extension_sma50_pct=5, score=score,
            )
        metrics = [
            metric(str(index), 90-index)
            for index in range(20)
        ]
        self.assertEqual(build_target_portfolio(metrics, False), [])
        target = build_target_portfolio(metrics, True)
        self.assertEqual(len(target), 15)
        self.assertTrue(all(abs(row["weight_pct"] - 100 / 15) < 1e-10 for row in target))

    def test_target_skips_shares_that_are_not_affordable(self):
        from momentum_strategy import MomentumMetric
        def metric(ticker, price, score):
            return MomentumMetric(
                ticker=ticker, price_usd=price, adv20_usd=6_000_000,
                sma20=19, sma50=18, sma50_1m_ago=17, sma200=15,
                sma200_1m_ago=14, return_1m_pct=8, return_3m_pct=20,
                return_6m_pct=30, spy_return_1m_pct=2,
                spy_return_3m_pct=5, relative_1m_pct=6,
                relative_3m_pct=15, volatility_pct=25,
                extension_sma50_pct=5, score=score,
            )
        metrics = [
            metric("EXPENSIVE", 1_000, 100),
            *[
                metric(str(index), 20, 90-index)
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
