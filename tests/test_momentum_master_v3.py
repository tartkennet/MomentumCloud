import tempfile
import unittest
from pathlib import Path

from momentum_master_v3 import load_history_cache, save_history_cache, simple_moving_average, update_buy_history


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
            self.assertEqual(second.loc[0, "Return_Since_Entry_pct"], 10.0)
            self.assertEqual(second.loc[0, "Return_1W_pct"], 10.0)


if __name__ == "__main__":
    unittest.main()
