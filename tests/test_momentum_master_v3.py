import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
