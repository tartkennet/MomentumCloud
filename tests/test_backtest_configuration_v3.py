import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backtest_momentum_v3 import (
    build_legacy_v1_metrics,
    choose_top,
    choose_top10,
    execution_price,
    find_unverified_split_basis_tickers,
    first_tradable_row,
    position_close_on_day,
    resolve_exit_execution,
)


class BacktestConfigurationTests(unittest.TestCase):
    def test_top_n_matches_requested_portfolio_size(self):
        metrics = [SimpleNamespace(ticker=str(i), total_score=float(i)) for i in range(20)]
        cache = {"2026-09-01": {}}
        with patch("backtest_momentum_v3.session_window", return_value=[]), patch(
            "backtest_momentum_v3.build_metrics", return_value=(metrics, {}, None)
        ):
            selected = choose_top(None, cache, [], "2026-09-01", 15)
            legacy = choose_top10(None, cache, [], "2026-09-01")
        self.assertEqual(len(selected), 15)
        self.assertEqual(selected[0].ticker, "19")
        self.assertEqual(len(legacy), 10)

    def test_top_n_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            choose_top(None, {}, [], "2026-09-01", 0)

    def test_next_open_uses_open_and_close_mode_uses_close(self):
        row = {"open": 98.0, "close": 101.0}
        self.assertEqual(execution_price(row, "next-open"), 98.0)
        self.assertEqual(execution_price(row, "next-close"), 101.0)

    def test_next_open_falls_back_to_close_when_open_is_unavailable(self):
        self.assertEqual(execution_price({"close": 101.0}, "next-open"), 101.0)

    def test_missing_execution_day_moves_to_first_tradable_session(self):
        days = ["2026-02-03", "2026-02-04", "2026-02-05"]
        cache = {
            "2026-02-03": {},
            "2026-02-04": {"HALT": {"open": 99.0, "close": 101.0}},
            "2026-02-05": {"HALT": {"open": 102.0, "close": 103.0}},
        }
        day, row = first_tradable_row(cache, days, "HALT", "2026-02-03")
        self.assertEqual(day, "2026-02-04")
        self.assertEqual(row["open"], 99.0)

    def test_missing_execution_reports_none_after_latest_allowed_day(self):
        days = ["2026-02-03", "2026-02-04"]
        cache = {
            "2026-02-03": {},
            "2026-02-04": {"HALT": {"open": 99.0, "close": 101.0}},
        }
        self.assertEqual(
            first_tradable_row(
                cache, days, "HALT", "2026-02-03", latest_day="2026-02-03"
            ),
            (None, None),
        )

    def test_cash_merger_settles_when_no_later_market_price_exists(self):
        days = ["2026-02-27", "2026-03-02", "2026-03-03"]
        cache = {
            "2026-02-27": {"FRGE": {"open": 44.0, "close": 44.5}},
            "2026-03-02": {},
            "2026-03-03": {},
        }
        day, row, action = resolve_exit_execution(
            cache,
            days,
            "FRGE",
            "2026-03-03",
            "2026-02-03",
            "2026-03-03",
        )
        self.assertEqual(day, "2026-03-02")
        self.assertEqual(row["close"], 45.0)
        self.assertEqual(action["reason"], "CASH_MERGER")

    def test_osh_cash_merger_settles_at_verified_consideration(self):
        days = ["2023-05-01", "2023-05-02", "2023-06-01"]
        cache = {
            "2023-05-01": {"OSH": {"open": 38.8, "close": 38.9}},
            "2023-05-02": {},
            "2023-06-01": {},
        }
        day, row, action = resolve_exit_execution(
            cache, days, "OSH", "2023-06-01", "2023-05-01", "2023-06-01"
        )
        self.assertEqual(day, "2023-05-02")
        self.assertEqual(row["close"], 39.0)
        self.assertEqual(action["reason"], "CASH_MERGER")

    def test_tradable_exit_before_cash_merger_keeps_market_price(self):
        days = ["2026-02-27", "2026-03-02", "2026-03-03"]
        cache = {
            "2026-02-27": {"FRGE": {"open": 44.0, "close": 44.5}},
            "2026-03-02": {},
            "2026-03-03": {},
        }
        day, row, action = resolve_exit_execution(
            cache,
            days,
            "FRGE",
            "2026-02-27",
            "2026-02-03",
            "2026-03-03",
        )
        self.assertEqual(day, "2026-02-27")
        self.assertEqual(row["open"], 44.0)
        self.assertIsNone(action)

    def test_stock_merger_uses_successor_at_original_share_ratio(self):
        days = ["2026-01-08", "2026-01-09", "2026-03-03"]
        cache = {
            "2026-01-08": {"HOUS": {"open": 12.0, "close": 12.5}},
            "2026-01-09": {"COMP": {"open": 8.0, "close": 8.5}},
            "2026-03-03": {"COMP": {"open": 10.0, "close": 10.5}},
        }
        day, row, action = resolve_exit_execution(
            cache, days, "HOUS", "2026-03-03", "2026-01-02", "2026-03-03"
        )
        self.assertEqual(day, "2026-03-03")
        self.assertAlmostEqual(row["open"], 14.36)
        self.assertEqual(action["reason"], "STOCK_MERGER")
        self.assertEqual(action["valuation_ticker"], "COMP")
        close, _ = position_close_on_day(cache, "HOUS", "2026-03-03")
        self.assertAlmostEqual(close, 10.5 * 1.436)

    def test_unverified_split_like_open_is_excluded_not_rewritten(self):
        days = ["2026-07-06", "2026-07-07"]
        cache = {
            "2026-07-06": {"TPC": {"open": 78.0, "close": 78.14}},
            "2026-07-07": {"TPC": {"open": 19.535, "close": 19.60}},
        }
        issues = find_unverified_split_basis_tickers(cache, days, ["TPC"], {})
        self.assertIn("TPC", issues)
        self.assertEqual(
            execution_price(
                cache["2026-07-07"]["TPC"],
                "next-open",
                reference_price=78.14,
                ticker="TPC",
            ),
            19.535,
        )

    def test_legacy_v1_uses_verified_equal_weight_return_score(self):
        closes = [200.0 - index * 0.5 for index in range(253)]
        history = [
            (f"day-{index:03d}", {"OLD": {"close": close}})
            for index, close in enumerate(closes)
        ]
        metrics = build_legacy_v1_metrics(
            ["OLD"], {"OLD": {"close": 200.0}}, history
        )
        expected_returns = [
            (200.0 / closes[index] - 1.0) * 100.0
            for index in (21, 63, 126, 252)
        ]
        self.assertEqual(len(metrics), 1)
        self.assertAlmostEqual(metrics[0].total_score, sum(expected_returns) / 4.0)

    def test_legacy_v1_rejects_nonpositive_momentum(self):
        flat_history = [
            (f"day-{index:03d}", {"FLAT": {"close": 100.0}})
            for index in range(253)
        ]
        self.assertEqual(
            build_legacy_v1_metrics(
                ["FLAT"], {"FLAT": {"close": 100.0}}, flat_history
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
