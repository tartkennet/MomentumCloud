"""Risk, causality and execution tests for the separate v2 research model."""
import unittest
from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np

import risk_managed_momentum as m
from run_risk_managed_research import actual_price, execute_lot


def history():
    first = date(2024, 1, 1)
    values = 100 * np.exp(np.arange(253) * .001 + .005 * np.sin(np.arange(253)))
    rows = []
    for i, price in enumerate(values):
        day = (first + timedelta(days=i)).isoformat()
        rows.append((day, {ticker: {"close": float(price), "volume": 1e9}
                           for ticker in ("AAA", "BBB", "SPY")}))
    return rows[::-1]


def candidates(hist):
    raw = {"AAA": 20., "BBB": 20.}
    dollars = {day: {"AAA": 25e6, "BBB": 25e6} for day, _ in hist}
    return m.rank_candidates(["BBB", "AAA"], hist, hist[0][0], raw, dollars)


class RiskManagedTests(unittest.TestCase):
    def test_invalid_risk_configuration_fails_closed(self):
        for params in ({"target_portfolio_volatility": float("nan")},
                       {"position_count": 0}, {"max_weight": 2}, {"stop_loss": 1}):
            with self.assertRaises(ValueError):
                m.RiskManagedConfig(**params)

    def test_deterministic_rank_and_raw_units(self):
        h = history()
        ranked, _ = candidates(h)
        self.assertEqual([c.ticker for c in ranked], ["AAA", "BBB"])
        self.assertEqual(ranked[0].raw_adv20, 25e6)
        # Huge adjusted price and volume cannot rescue a raw price below $10.
        dollars = {day: {"AAA": 25e6} for day, _ in h}
        ranked, counts = m.rank_candidates(["AAA"], h, h[0][0], {"AAA": 9.99}, dollars)
        self.assertEqual(ranked, [])
        self.assertEqual(counts, {"raw_price_floor": 1})

    def test_raw_liquidity_and_all_twenty_observations_required(self):
        h = history()
        dollars = {day: {"AAA": 19e6} for day, _ in h}
        ranked, counts = m.rank_candidates(["AAA"], h, h[0][0], {"AAA": 20}, dollars)
        self.assertEqual(ranked, [])
        self.assertEqual(counts, {"raw_liquidity_floor": 1})
        dollars[h[10][0]].pop("AAA")
        _, counts = m.rank_candidates(["AAA"], h, h[0][0], {"AAA": 20}, dollars)
        self.assertEqual(counts, {"missing_raw_adv20": 1})

    def test_future_data_and_disordered_history_are_rejected(self):
        h = history()
        with self.assertRaises(ValueError):
            m.history_before(h, h[1][0])
        with self.assertRaises(ValueError):
            m.history_before([h[1], h[0], *h[2:]], h[0][0])

    def test_recent_shock_rejected_without_a_ticker_blacklist(self):
        h = history()
        for i in range(10):
            h[i][1]["AAA"]["close"] *= 1.26
        ranked, counts = candidates(h)
        self.assertEqual([c.ticker for c in ranked], ["BBB"])
        self.assertEqual(counts, {"recent_daily_jump": 1})

    def test_capped_weights_keep_cash_and_do_not_borrow(self):
        weights = m.capped_inverse_volatility([.01, .2, .4], .12, .05)
        self.assertAlmostEqual(weights.sum(), .12)
        self.assertAlmostEqual(weights[0], .05)
        self.assertLess(weights[2], weights[1])
        self.assertTrue((weights <= .05).all())
        with self.assertRaises(ValueError):
            m.capped_inverse_volatility([np.nan], 1, .05)

    def test_correlated_risk_is_scaled_using_covariance(self):
        h = history()
        # Give all 25 names the same 40%-volatility return path. Covariance
        # must not incorrectly divide their shared risk by sqrt(25).
        chronological = 100 * np.cumprod(1 + .001 + .025 * np.sin(np.arange(253)))
        for i, (_, rows) in enumerate(h):
            for n in range(25):
                rows[str(n)] = {"close": float(chronological[252-i])}
        base = candidates(history())[0][0]
        selected = [replace(base, ticker=str(n)) for n in range(25)]
        weights, info = m.allocation(selected, h, h[0][0])
        self.assertLess(sum(weights.values()), 1)
        self.assertAlmostEqual(info["forecast_volatility"], .15)
        self.assertLessEqual(max(weights.values()), .05)

    def test_vacant_positions_do_not_force_investment(self):
        h = history()
        selected = candidates(h)[0][:1]
        weights, info = m.allocation(selected, h, h[0][0])
        self.assertAlmostEqual(sum(weights.values()), 1/25)
        self.assertAlmostEqual(info["cash_weight"], 24/25)

    def test_missing_spy_does_not_create_risk_on(self):
        h = history()
        h[100][1].pop("SPY")
        with self.assertRaises(ValueError):
            m.spy_risk_on(h)

    def test_exact_open_required_and_gapped_stop_is_not_capped(self):
        days = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
        cache = {day: {"AAA": {"open": opening, "close": close}} for day, opening, close in
                 zip(days, [100, 100, 60, 60], [100, 85, 60, 60])}
        engine = SimpleNamespace(
            get_from_map=lambda rows, ticker: rows.get(ticker),
            execution_price=lambda row, *args: row["open"],
            position_close_on_day=lambda cache, ticker, day, entry: (cache[day][ticker]["close"], None),
            resolve_exit_execution=lambda cache, days, ticker, target, entry, planned: (target, cache[target][ticker], None))
        candidate = replace(candidates(history())[0][0], ticker="AAA", price=100)
        period = SimpleNamespace(SignalDate="2023-12-31", EntryDate=days[0], ExitDate=days[-1])
        lot = execute_lot(engine, cache, days, {}, candidate, period, .04, None)
        self.assertEqual(lot["TriggerDate"], days[1])
        self.assertEqual(lot["ExitDate"], days[2])
        self.assertAlmostEqual(lot["GrossReturn_pct"], -40)
        lot = execute_lot(engine, cache, days, {}, candidate, period, .04, days[1])
        self.assertEqual(lot["ExitReason"], "MARKET_RISK_OFF")
        self.assertEqual(lot["ExitDate"], days[1])
        # Later missing stock closes cannot affect an already completed exit.
        cache[days[2]]["AAA"].pop("close")
        lot = execute_lot(engine, cache, days, {}, candidate, period, .04, days[1])
        self.assertEqual(lot["ExitDate"], days[1])
        cache[days[0]]["AAA"].pop("open")
        with self.assertRaises(RuntimeError):
            actual_price(engine, cache, days, {}, "AAA", days[0])

    def test_cash_merger_ends_stop_monitoring(self):
        days = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
        cache = {days[0]: {"AAA": {"open": 100, "close": 100}}}
        engine = SimpleNamespace(
            CASH_CORPORATE_ACTIONS={"AAA": {"effective_date": days[1]}},
            get_from_map=lambda rows, ticker: rows.get(ticker),
            execution_price=lambda row, *args: row["open"],
            position_close_on_day=lambda cache, ticker, day, entry: (cache[day][ticker]["close"], None),
            resolve_exit_execution=lambda cache, days, ticker, target, entry, planned:
                (days[1], {"close": 110}, {"reason": "CASH_MERGER"}))
        candidate = replace(candidates(history())[0][0], ticker="AAA", price=100)
        period = SimpleNamespace(SignalDate="2023-12-31", EntryDate=days[0], ExitDate=days[-1])
        lot = execute_lot(engine, cache, days, {}, candidate, period, .04, None)
        self.assertEqual(lot["ExitDate"], days[1])
        self.assertEqual(lot["ExitReason"], "CASH_MERGER")
        self.assertAlmostEqual(lot["GrossReturn_pct"], 10)


if __name__ == "__main__":
    unittest.main()
