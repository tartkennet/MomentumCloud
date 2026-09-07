import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backtest_momentum_v3 import (
    build_legacy_v1_metrics,
    choose_top,
    choose_top10,
    execution_price,
    first_tradable_row,
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
