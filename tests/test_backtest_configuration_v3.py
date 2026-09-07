import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backtest_momentum_v3 import choose_top, choose_top10, execution_price


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


if __name__ == "__main__":
    unittest.main()
