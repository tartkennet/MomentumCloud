import unittest
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile

from selection_v3_execution import documented_unfilled_entry, install_action, install_disclosed_stale_marks


class SelectionExecutionTests(unittest.TestCase):
    def stale_fixture(self, bad_raw=False):
        days = ["2024-01-01", "2024-01-02", "2024-01-03"]
        row = lambda price: dict(open=price, high=price, low=price, close=price)
        cache = {days[0]: {"AAA": row(10)}, days[1]: {}, days[2]: {"AAA": row(11)}}
        def original(cache, ticker, day, entry=None):
            value = cache.get(day, {}).get(ticker)
            return (value["close"] if value else None), None
        engine = SimpleNamespace(position_close_on_day=original,
                                 get_from_map=lambda rows, ticker: rows.get(ticker))
        records = []
        for adjusted in ("true", "false"):
            prices = [10, 11] if not bad_raw or adjusted == "true" else [5, 5.5]
            lines = ["v,vw,o,c,h,l,t,n"]
            for day, price in zip((days[0], days[2]), prices):
                ms = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)
                lines.append(f"100,10,{price},{price},{price},{price},{ms},1")
            records.append({"ticker":"AAA","adjusted":adjusted,
                            "request":{"path":"/v2/aggs/ticker/AAA/range/1/day/2024-01-01/2024-01-03"},
                            "response":"\n".join(lines)})
        return days, cache, engine, records

    def test_stale_mark_is_dated_disclosed_and_cannot_use_future_or_change_cache(self):
        days, cache, engine, records = self.stale_fixture()
        before = json.dumps(cache,sort_keys=True)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"source.json";p.write_text(json.dumps(records))
            uses=install_disclosed_stale_marks(engine,cache,days,[p],{"variant":"test","stage":"NAV"})
            self.assertEqual(engine.position_close_on_day(cache,"AAA",days[1],days[0]),(10,None))
            self.assertEqual(next(iter(uses.values()))["last_observed_day"],days[0])
            self.assertFalse(next(iter(uses.values()))["fresh_close_observed"])
            # There is no preceding observed holding mark for a later entry.
            self.assertEqual(engine.position_close_on_day(cache,"AAA",days[1],days[1]),(None,None))
            self.assertEqual(json.dumps(cache,sort_keys=True),before)
            # The missing opening execution remains missing.
            self.assertIsNone(engine.get_from_map(cache[days[1]],"AAA"))

    def test_incompatible_stale_mark_bases_are_blocking(self):
        days,cache,engine,records=self.stale_fixture(bad_raw=True)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"source.json";p.write_text(json.dumps(records))
            with self.assertRaises(RuntimeError):
                install_disclosed_stale_marks(engine,cache,days,[p],{})

    def test_only_documented_nontradable_entry_retains_cash(self):
        engine = SimpleNamespace(get_from_map=lambda rows, ticker: rows.get(ticker))
        self.assertIsNone(documented_unfilled_entry(engine, {}, "UNKNOWN", "2024-12-02"))
        self.assertIsNone(documented_unfilled_entry(engine, {}, "LBPH", "2024-11-29"))
        status = documented_unfilled_entry(engine, {}, "LBPH", "2024-12-02")
        self.assertEqual(status["status"], "DOCUMENTED_UNFILLED_ORDER")
        self.assertIn("ECA2024-589", status["source"])
        self.assertEqual(documented_unfilled_entry(engine, {}, "EVRI", "2025-07-01")["status"],
                         "DOCUMENTED_UNFILLED_ORDER")

    def test_conflicting_print_is_not_silently_discarded(self):
        engine = SimpleNamespace(get_from_map=lambda rows, ticker: rows.get(ticker))
        with self.assertRaises(RuntimeError):
            documented_unfilled_entry(engine, {"2024-12-02": {"LBPH": {"open": 60}}},
                                      "LBPH", "2024-12-02")

    def test_usx_keeps_true_nontrading_effective_day_and_legal_amount(self):
        engine = SimpleNamespace(CASH_CORPORATE_ACTIONS={"OTHER": {"unchanged": True}})
        install_action(engine)
        action = engine.CASH_CORPORATE_ACTIONS["USX"]
        self.assertEqual(action["effective_date"], "2023-07-01")
        self.assertEqual(action["cash_per_share"], 6.15)
        self.assertTrue(engine.CASH_CORPORATE_ACTIONS["OTHER"]["unchanged"])


if __name__ == "__main__":
    unittest.main()
