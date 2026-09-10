import json
import tempfile
import unittest
from pathlib import Path

from momentum_master_v3 import (
    adjust_history_cache_for_splits,
    load_history_cache,
    load_history_cache_state,
    save_history_cache,
)


class HistoryCacheSplitBasisTests(unittest.TestCase):
    def test_legacy_cache_without_basis_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            path.write_text(
                json.dumps({"version": 1, "sessions": {"2026-07-02": {}}}),
                encoding="utf-8",
            )
            sessions, adjusted_through = load_history_cache_state(str(path))
            self.assertEqual(sessions, {})
            self.assertIsNone(adjusted_through)
            self.assertEqual(load_history_cache(str(path)), {})

    def test_split_restates_older_history_once(self):
        sessions = {
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

        applied = adjust_history_cache_for_splits(
            sessions,
            [event],
            "2026-07-01",
            "2026-09-08",
        )

        self.assertEqual(applied, 1)
        self.assertAlmostEqual(sessions["2026-07-02"]["TPC"]["open"], 20.0)
        self.assertAlmostEqual(sessions["2026-07-02"]["TPC"]["close"], 19.875)
        self.assertAlmostEqual(sessions["2026-07-02"]["TPC"]["volume"], 4000.0)
        self.assertAlmostEqual(sessions["2026-07-07"]["TPC"]["open"], 19.5)

        applied_again = adjust_history_cache_for_splits(
            sessions,
            [event],
            "2026-09-08",
            "2026-09-08",
        )
        self.assertEqual(applied_again, 0)
        self.assertAlmostEqual(sessions["2026-07-02"]["TPC"]["close"], 19.875)

    def test_v2_round_trip_preserves_basis(self):
        maps = [("2026-07-02", {"TPC": {"close": 19.875, "volume": 4000.0}})]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            save_history_cache(str(path), maps, "2026-09-08")
            sessions, adjusted_through = load_history_cache_state(str(path))
            self.assertEqual(sessions, dict(maps))
            self.assertEqual(adjusted_through, "2026-09-08")


if __name__ == "__main__":
    unittest.main()
