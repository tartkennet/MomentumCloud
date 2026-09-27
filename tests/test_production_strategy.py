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
        self.assertEqual(PRODUCTION.selection_model, "market-leaders-v1")
        self.assertEqual(PRODUCTION.position_count, 15)
        self.assertEqual(PRODUCTION.candidate_count, 50)
        self.assertEqual(PRODUCTION.min_price_usd, 10.0)
        self.assertEqual(PRODUCTION.min_adv20_usd, 5_000_000.0)
        self.assertEqual(PRODUCTION.stop_loss_pct, 10.0)
        self.assertEqual(PRODUCTION.trend_lookback_sessions, 252)
        self.assertEqual(PRODUCTION.minimum_positive_months, 8)
        self.assertEqual(PRODUCTION.max_annualized_volatility_pct, 45.0)
        self.assertEqual(PRODUCTION.max_extension_sma50_pct, 20.0)

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

    def test_persistent_efficient_trend_drives_score(self):
        steady = [150.0 - 50.0 * index / 252.0 for index in range(253)]
        fresher = [170.0 - 70.0 * index / 252.0 for index in range(253)]
        ranked = rank_universe(
            ["STEADY", "FRESHER"],
            history_for({"STEADY": steady, "FRESHER": fresher}),
        )
        self.assertEqual(ranked[0].ticker, "FRESHER")
        self.assertGreaterEqual(ranked[0].positive_months, 8)
        self.assertGreater(ranked[0].trend_efficiency_pct, 0.0)
        self.assertEqual(
            ranked[0].score,
            ranked[0].trend_efficiency_pct * ranked[0].mom12_2_pct,
        )

    def test_lagging_spy_is_ineligible(self):
        fresh = [140.0 - 40.0 * index / 252.0 for index in range(253)]
        lagging = [120.0 - 20.0 * index / 252.0 for index in range(253)]
        spy = [130.0 - 30.0 * index / 252.0 for index in range(253)]
        ranked = rank_universe(
            ["FRESH", "LAGGING"],
            history_for({"FRESH": fresh, "LAGGING": lagging, "SPY": spy}),
        )
        self.assertEqual([row.ticker for row in ranked], ["FRESH"])

    def test_market_leader_requires_persistent_positive_months(self):
        laggard = [150.0 - 50.0 * index / 252.0 for index in range(253)]
        leader = [180.0 - 80.0 * index / 252.0 for index in range(253)]
        spy = [160.0 - 60.0 * index / 252.0 for index in range(253)]
        ranked = rank_universe(
            ["LAGGARD", "LEADER"],
            history_for({"LAGGARD": laggard, "LEADER": leader, "SPY": spy}),
        )
        self.assertEqual([row.ticker for row in ranked], ["LEADER"])
        self.assertGreaterEqual(ranked[0].positive_months, 8)

    def test_split_sized_adjusted_price_discontinuity_is_rejected(self):
        clean = [130.0 - 30.0 * index / 252.0 for index in range(253)]
        broken = list(clean)
        broken[100] = broken[99] / 4.0
        ranked = rank_universe(
            ["CLEAN", "BROKEN"],
            history_for({"CLEAN": clean, "BROKEN": broken}),
        )
        self.assertEqual([row.ticker for row in ranked], ["CLEAN"])

    def test_spy_regime_requires_confirmed_dual_trend(self):
        flat = [100.0] * 253
        risk_on = history_for({"SPY": flat})
        risk_on[0][1]["SPY"]["close"] = 101.0
        self.assertEqual(market_regime(risk_on)["status"], "RISK ON")
        self.assertEqual(market_regime(history_for({"SPY": flat}))["status"], "RISK OFF")
        weak = [100.0 + 30.0 * index / 252.0 for index in range(253)]
        weak[0] = 101.0
        self.assertEqual(market_regime(history_for({"SPY": weak}))["status"], "RISK OFF")

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
            portfolio_value_sek=12_000,
            usdsek=10,
        )
        self.assertEqual(len(target), 15)
        self.assertNotIn("EXPENSIVE", {row["ticker"] for row in target})
        self.assertTrue(all(row["quantity"] >= 1 for row in target))
        self.assertEqual([row["target_rank"] for row in target], list(range(1, 16)))

    def test_monthly_rebalance_uses_current_ranking_not_legacy_retention(self):
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

        ranked = [metric(str(index), 100 - index) for index in range(21)]
        target = build_target_portfolio(ranked, True, previous_tickers=["15", "20"])
        tickers = {row["ticker"] for row in target}
        self.assertNotIn("15", tickers)
        self.assertNotIn("20", tickers)
        self.assertEqual(len(target), PRODUCTION.position_count)

    def test_stop_loss_is_locked_to_ten_percent(self):
        self.assertFalse(stop_is_triggered(90.01, 100.0))
        self.assertTrue(stop_is_triggered(90.0, 100.0))


if __name__ == "__main__":
    unittest.main()
