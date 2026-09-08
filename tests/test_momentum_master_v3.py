import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from momentum_master_v3 import apply_positive_negative_formatting, build_holdings_df, split_price_factor, load_history_cache, save_history_cache, simple_moving_average, update_buy_history


class SimpleMovingAverageTests(unittest.TestCase):
    def test_uses_latest_trading_sessions(self):
        closes = [float(value) for value in range(253, 0, -1)]

        self.assertEqual(simple_moving_average(closes, 50), 228.5)
        self.assertEqual(simple_moving_average(closes, 200), 153.5)

    def test_requires_enough_history(self):
        self.assertIsNone(simple_moving_average([10.0] * 49, 50))


    def test_history_cache_round_trip(self):
        sessions = [("2026-09-01", {"ABC": {"close": 10.5, "volume": 200.0}})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            save_history_cache(str(path), sessions)
            self.assertEqual(
                load_history_cache(str(path)),
                {"2026-09-01": {"ABC": {"close": 10.5, "volume": 200.0}}},
            )


    def test_buy_history_tracks_entry_and_current_return(self):
        buy = __import__("pandas").DataFrame([{"Ticker": "ABC", "Rank": 1, "Price_USD": 10.0, "TotalScore": 42.0}])
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "history.csv")
            first = update_buy_history(buy, {"ABC": {"close": 10.0, "volume": 1}}, "2026-09-01", path)
            second = update_buy_history(buy.iloc[0:0], {"ABC": {"close": 11.0, "volume": 1}}, "2026-09-09", path)
            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertAlmostEqual(second.loc[0, "Return_Since_Entry_pct"], 10.0, places=8)
            self.assertAlmostEqual(second.loc[0, "Return_1W_pct"], 10.0, places=8)


    def test_holdings_compare_to_spy_and_current_rank(self):
        pd = __import__("pandas")
        portfolio = pd.DataFrame([{
            "Ticker": "ABC", "Qty": 2, "EntryDate": "2026-09-01",
            "EntryPrice_USD": 10.0, "EntryFX": 10.0, "EntryFees_SEK": 0.0,
        }])
        latest = {"ABC": {"close": 11.0, "volume": 1}, "SPY": {"close": 110.0, "volume": 1}}
        candidates = pd.DataFrame([{"Ticker": "ABC", "Rank": 1}])
        history = [
            ("2026-09-03", latest),
            ("2026-09-01", {"ABC": {"close": 10.0, "volume": 1}, "SPY": {"close": 100.0, "volume": 1}}),
        ]
        holdings = build_holdings_df(portfolio, latest, 10.0, candidates, history)
        self.assertAlmostEqual(holdings.loc[0, "P&L_pct"], 10.0, places=8)
        self.assertAlmostEqual(holdings.loc[0, "SPY_Return_SEK_pct"], 10.0, places=8)
        self.assertAlmostEqual(holdings.loc[0, "Edge_vs_SPY_pct"], 0.0, places=8)
        self.assertEqual(holdings.loc[0, "MomentumStatus"], "TOP10")


    def test_return_columns_get_positive_negative_formatting(self):
        from openpyxl import Workbook
        ws = Workbook().active
        ws.append(["Ticker", "Ret1m", "P&L_SEK", "Price_USD"])
        ws.append(["ABC", 1.0, -10.0, 20.0])
        apply_positive_negative_formatting(ws)
        self.assertEqual(len(ws.conditional_formatting), 2)


    def test_split_price_factor_normalizes_entry_price(self):
        events = [{"execution_date": "2026-09-03", "split_from": 1, "split_to": 2}]
        self.assertAlmostEqual(split_price_factor(events, "2026-09-01", "2026-09-03"), 0.5)
        self.assertAlmostEqual(split_price_factor(events, "2026-09-03", "2026-09-04"), 1.0)


from backtest_momentum_v3 import calendar_rebalance_signals, daily_portfolio_max_drawdown, execution_periods, execution_price, rebalance_point_max_drawdown, research_exit, stop_loss_exit


class BacktestTimingTests(unittest.TestCase):
    def test_next_open_normalizes_verified_split_mismatch(self):
        row = {"open": 17.33, "close": 86.80, "volume": 1}
        events = [{
            "ticker": "TPC", "execution_date": "2026-08-04",
            "split_from": 1, "split_to": 5,
        }]
        self.assertAlmostEqual(
            execution_price(row, "next-open", events, "2026-08-04"),
            86.65,
            places=8,
        )
        self.assertEqual(
            execution_price(row, "next-open", events, "2026-08-05"),
            17.33,
        )
        self.assertAlmostEqual(
            execution_price(row, "next-open"),
            86.65,
            places=8,
        )

    def test_calendar_rebalances_use_first_session_every_nth_month(self):
        days = ["2026-03-06", "2026-03-09", "2026-04-01", "2026-05-01", "2026-06-01"]
        self.assertEqual(
            calendar_rebalance_signals(days, "2026-03-06", "2026-06-01", 2),
            ["2026-03-06", "2026-05-01"],
        )

    def test_rebalance_point_drawdown(self):
        self.assertAlmostEqual(rebalance_point_max_drawdown([110, 121, 90, 99]), -25.6198347107, places=7)

    def test_stop_loss_signals_at_close_and_exits_next_session(self):
        days = ["2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]
        cache = {
            "2026-06-02": {"ABC": {"close": 100.0, "volume": 1}},
            "2026-06-03": {"ABC": {"close": 89.0, "volume": 1}},
            "2026-06-04": {"ABC": {"close": 87.0, "volume": 1}},
            "2026-06-05": {"ABC": {"close": 95.0, "volume": 1}},
        }
        self.assertEqual(
            stop_loss_exit(cache, days, "ABC", "2026-06-02", "2026-06-05", 10),
            ("2026-06-04", "STOP_LOSS"),
        )
        self.assertEqual(
            stop_loss_exit(cache, days, "ABC", "2026-06-02", "2026-06-05", None),
            ("2026-06-05", "REBALANCE"),
        )

    def test_stop_loss_is_measured_from_actual_next_open_entry(self):
        days = ["2026-06-02", "2026-06-03", "2026-06-04"]
        cache = {
            "2026-06-02": {"ABC": {"open": 90.0, "close": 100.0, "volume": 1}},
            "2026-06-03": {"ABC": {"open": 86.0, "close": 85.0, "volume": 1}},
            "2026-06-04": {"ABC": {"open": 84.0, "close": 84.0, "volume": 1}},
        }
        self.assertEqual(
            research_exit(
                cache,
                days,
                "ABC",
                "2026-06-02",
                "2026-06-04",
                "stop",
                10,
                "next-open",
            ),
            ("2026-06-04", "REBALANCE"),
        )

    def test_sma50_exit_is_executed_next_session(self):
        dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(52)]
        cache = {
            day: {"ABC": {"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1}}
            for day in dates
        }
        cache[dates[49]]["ABC"]["close"] = 80.0
        self.assertEqual(
            research_exit(cache, dates, "ABC", dates[49], dates[51], "sma50", None),
            (dates[50], "BELOW_SMA50"),
        )

    def test_daily_drawdown_holds_stopped_position_as_cash(self):
        positions = [{
            "EntryDate": "2026-06-02", "PlannedExitDate": "2026-06-05",
            "ExitDate": "2026-06-04", "ExitPrice_USD": 90.0,
            "EntryPrice_USD": 100.0, "Ticker": "ABC",
        }]
        cache = {
            "2026-06-02": {"ABC": {"close": 100.0, "volume": 1}},
            "2026-06-03": {"ABC": {"close": 95.0, "volume": 1}},
            "2026-06-04": {"ABC": {"close": 80.0, "volume": 1}},
            "2026-06-05": {"ABC": {"close": 120.0, "volume": 1}},
        }
        drawdown = daily_portfolio_max_drawdown(positions, cache, sorted(cache))
        self.assertAlmostEqual(drawdown, -10.3, places=7)

    def test_execution_is_after_signal_and_exits_at_next_execution(self):
        days = ["2026-03-02", "2026-03-03", "2026-03-04", "2026-04-01", "2026-04-02", "2026-04-03"]
        periods = execution_periods(days, ["2026-03-02", "2026-04-01"], "2026-04-03")
        self.assertEqual(periods, [
            ("2026-03-02", "2026-03-03", "2026-04-02"),
            ("2026-04-01", "2026-04-02", "2026-04-03"),
        ])
        self.assertTrue(all(signal < entry <= exit_day for signal, entry, exit_day in periods))


if __name__ == "__main__":
    unittest.main()
