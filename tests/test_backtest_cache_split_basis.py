import json
import tempfile
import unittest
from pathlib import Path

from backtest_momentum_v3 import (
    adjust_cached_history_for_splits,
    load_backtest_cache,
    save_backtest_cache,
)


class BacktestCacheSplitBasisTests(unittest.TestCase):
    def test_legacy_cache_without_basis_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text(
                json.dumps({"version": 1, "sessions": {"2026-07-02": {}}}),
                encoding="utf-8",
            )
            sessions, adjusted_through = load_backtest_cache(path)
            self.assertEqual(sessions, {})
            self.assertIsNone(adjusted_through)

    def test_split_moves_older_rows_to_new_basis_once(self):
        cache = {
            "2026-07-02": {
                "TPC": {
                    "open": 80.0,
                    "high": 84.0,
                    "low": 76.0,
                    "close": 79.5,
                    "volume": 1000.0,
                }
            },
            "2026-07-07": {
                "TPC": {
                    "open": 19.5,
                    "high": 20.5,
                    "low": 19.0,
                    "close": 19.6,
                    "volume": 4000.0,
                }
            },
        }
        event = {
            "ticker": "TPC",
            "execution_date": "2026-07-07",
            "split_from": 1,
            "split_to": 4,
        }

        applied = adjust_cached_history_for_splits(
            cache,
            [event],
            "2026-07-01",
            "2026-09-08",
        )

        self.assertEqual(applied, 1)
        self.assertAlmostEqual(cache["2026-07-02"]["TPC"]["open"], 20.0)
        self.assertAlmostEqual(cache["2026-07-02"]["TPC"]["close"], 19.875)
        self.assertAlmostEqual(cache["2026-07-02"]["TPC"]["volume"], 4000.0)
        self.assertAlmostEqual(cache["2026-07-07"]["TPC"]["open"], 19.5)

        applied_again = adjust_cached_history_for_splits(
            cache,
            [event],
            "2026-09-08",
            "2026-09-08",
        )
        self.assertEqual(applied_again, 0)
        self.assertAlmostEqual(cache["2026-07-02"]["TPC"]["close"], 19.875)

    def test_v2_round_trip_preserves_basis(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            expected = {"2026-07-02": {"TPC": {"close": 19.875, "volume": 4000.0}}}
            save_backtest_cache(path, expected, "2026-09-08")
            sessions, adjusted_through = load_backtest_cache(path)
            self.assertEqual(sessions, expected)
            self.assertEqual(adjusted_through, "2026-09-08")


if __name__ == "__main__":
    unittest.main()
