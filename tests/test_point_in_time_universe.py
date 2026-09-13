import json
import tempfile
import unittest
from pathlib import Path

from backtest_momentum_v3 import (
    fetch_point_in_time_universe,
    load_point_in_time_universe_cache,
    point_in_time_universes,
    save_point_in_time_universe_cache,
)


class FakeReferenceClient:
    def __init__(self):
        self.calls = []

    def _get(self, path, params):
        self.calls.append((path, params))
        if len(self.calls) == 1:
            return {
                "results": [
                    {"ticker": "GOOD", "active": True, "primary_exchange": "XNAS", "type": "CS"},
                    {"ticker": "ETF", "active": True, "primary_exchange": "XNAS", "type": "ETF"},
                    {"ticker": "OTC", "active": True, "primary_exchange": "PINX", "type": "CS"},
                ],
                "next_url": "https://api.polygon.io/v3/reference/tickers?cursor=second",
            }
        return {
            "results": [
                {"ticker": "NYSE", "active": True, "primary_exchange": "XNYS", "type": "CS"},
                {"ticker": "PREF", "active": True, "primary_exchange": "XNYS", "type": "PFD"},
            ]
        }


class PointInTimeUniverseTests(unittest.TestCase):
    def test_reference_universe_is_paginated_and_filters_non_common_stock(self):
        client = FakeReferenceClient()
        tickers = fetch_point_in_time_universe(client, "2025-12-31")
        self.assertEqual(tickers, ["GOOD", "NYSE"])
        self.assertEqual(client.calls[0][1]["type"], "CS")
        self.assertEqual(client.calls[1][0], "/v3/reference/tickers")
        self.assertEqual(client.calls[1][1], {"cursor": "second"})

    def test_universe_cache_round_trip_and_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universes.json"
            save_point_in_time_universe_cache(path, {"2025-12-31": ["B", "A"]})
            self.assertEqual(
                load_point_in_time_universe_cache(path),
                {"2025-12-31": ["A", "B"]},
            )

            class MustNotFetch:
                def _get(self, path, params):
                    raise AssertionError("cached universe should be reused")

            self.assertEqual(
                point_in_time_universes(
                    MustNotFetch(), ["2025-12-31"], cache_path=path
                ),
                {"2025-12-31": ["A", "B"]},
            )

    def test_unknown_cache_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universes.json"
            path.write_text(json.dumps({"version": 0, "dates": {}}), encoding="utf-8")
            self.assertEqual(load_point_in_time_universe_cache(path), {})


if __name__ == "__main__":
    unittest.main()
