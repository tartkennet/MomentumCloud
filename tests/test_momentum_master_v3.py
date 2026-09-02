import tempfile
import unittest
from pathlib import Path

from momentum_master_v3 import load_history_cache, save_history_cache, simple_moving_average


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


if __name__ == "__main__":
    unittest.main()
