import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from momentum_core import (
    CONFIG, DataBlocked, Ledger, adjusted_history, capped_weights, gates,
    metrics, risk_on, select_targets,
)
from momentum_core_data import CoreData, atomic_json, paginate
from run_momentum_core import replay, resume_paper, run, verify_forward_prefix


class MemoryData:
    def __init__(self, days, bars, records=None, splits=None, dividends=None,
                 cash_actions=None, stock_actions=None):
        self.days = days
        self.sessions = days
        self.by_day = dict(zip(days, bars))
        self.records = records or []
        self.splits = splits or []
        self.dividends = dividends or []
        self.cash_actions = cash_actions or {}
        self.stock_actions = stock_actions or {}

    def bars(self, day):
        return self.by_day[day]

    def history(self, day, ticker, count):
        end = self.days.index(day) + 1
        return [(d, self.by_day[d].get(ticker)) for d in reversed(self.days[max(0, end-count):end])]

    def universe(self, day):
        return self.records


def long_data(year=2023):
    days = [(date(year, 1, 1) + timedelta(days=i)).isoformat() for i in range(300)]
    records = [{"ticker": f"S{k:02}", "type": "CS", "active": True,
                "primary_exchange": "XNYS", "name": f"Company {k}"} for k in range(20)]
    bars = []
    for i in range(300):
        row = {"SPY": [100 + i, 100 + i, 1_000_000]}
        for k in range(20):
            price = 30 * math.exp(i * (0.001 + k * 0.0001) + math.sin(i) * 0.01)
            row[f"S{k:02}"] = [price, price, 1_000_000]
        bars.append(row)
    return MemoryData(days, bars, records)


def order(day, nav, **weights):
    return {"signal_date": day, "signal_nav": nav,
            "targets": [{"ticker": t, "weight": w} for t, w in weights.items()]}


class SelectionTests(unittest.TestCase):
    def test_one_rank_and_caps_not_score_blend(self):
        data = long_data()
        selected, count = select_targets(data, data.days[-1])
        self.assertEqual(count, 20)
        self.assertEqual(len(selected), 15)
        self.assertEqual(selected[0]["ticker"], "S19")
        self.assertEqual(selected[-1]["ticker"], "S05")
        self.assertAlmostEqual(sum(r["weight"] for r in selected), 1)
        self.assertTrue(all(0 < r["weight"] <= .1 + 1e-12 for r in selected))

    def test_past_signal_unchanged_by_future_prices_or_split(self):
        data = long_data()
        signal = data.days[-2]
        before = select_targets(data, signal)
        data.by_day[data.days[-1]]["S19"] = [0.01, 0.01, 1]
        data.splits.append({"ticker": "S19", "execution_date": data.days[-1],
                            "split_from": 1, "split_to": 100})
        self.assertEqual(select_targets(data, signal), before)

    def test_nominal_floor_not_changed_by_future_reverse_split(self):
        data = long_data()
        day = data.days[-2]
        data.by_day[day]["S19"][1] = 9.0
        data.splits.append({"ticker": "S19", "execution_date": data.days[-1],
                            "split_from": 100, "split_to": 1})
        chosen, _ = select_targets(data, day)
        self.assertNotIn("S19", [r["ticker"] for r in chosen])

    def test_missing_history_not_backfilled(self):
        data = long_data()
        del data.by_day[data.days[-100]]["S19"]
        chosen, _ = select_targets(data, data.days[-1])
        self.assertNotIn("S19", [r["ticker"] for r in chosen])

    def test_pit_metadata_excludes_ineligible_name(self):
        data = long_data()
        data.records[-1]["name"] = "Future Acquisition Corp"
        chosen, _ = select_targets(data, data.days[-1])
        self.assertNotIn("S19", [r["ticker"] for r in chosen])

    def test_missing_sleeves_cash_and_concentrated_weights_capped(self):
        weights = capped_weights({"A": 100, "B": 1}, .1, 2 / 15)
        self.assertAlmostEqual(sum(weights.values()), 2 / 15)
        self.assertLessEqual(weights["A"], .1)
        self.assertEqual(capped_weights({}, .1), {})

    def test_weights_stable_across_python_process_hash_seeds(self):
        code = ("import json; from momentum_core import capped_weights; "
                "print(json.dumps(capped_weights({f'S{k}': 10**(k/13) for k in range(15)}, .1), sort_keys=True))")
        outputs = [subprocess.check_output([sys.executable, "-c", code],
                   env=dict(os.environ, PYTHONHASHSEED=str(seed))) for seed in (1, 2, 3)]
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])

    def test_risk_off_and_incomplete_spy_fail(self):
        data = long_data()
        self.assertTrue(risk_on(data, data.days[-1]))
        data.by_day[data.days[-1]]["SPY"][1] = 1
        self.assertFalse(risk_on(data, data.days[-1]))
        del data.by_day[data.days[-30]]["SPY"]
        with self.assertRaises(DataBlocked):
            risk_on(data, data.days[-1])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.days = ["2024-01-02", "2024-01-03", "2024-01-04"]
        self.data = MemoryData(self.days, [{"A": [100, 100, 1_000_000]} for _ in self.days])

    def test_signal_cannot_fill_on_same_close(self):
        ledger = Ledger(cash=1000, pending=order(self.days[0], 1000, A=.5))
        with self.assertRaises(ValueError):
            ledger.execute_open(self.data, self.days[0])
        self.data.by_day[self.days[1]]["A"][0] = 125
        ledger.execute_open(self.data, self.days[1])
        self.assertEqual(ledger.shares, {"A": 4})
        self.assertAlmostEqual(ledger.cash, 499.25)

    def test_cash_cannot_go_negative_with_gap_and_fees(self):
        ledger = Ledger(cash=1000, pending=order(self.days[0], 1000, A=1))
        ledger.execute_open(self.data, self.days[1])
        self.assertEqual(ledger.shares["A"], 9)
        self.assertGreaterEqual(ledger.cash, 0)
        self.assertAlmostEqual(ledger.fees, 1.35)

    def test_unchanged_shares_have_no_monthly_fee(self):
        ledger = Ledger(cash=100, shares={"A": 9}, pending=order(self.days[0], 1000, A=.9))
        ledger.execute_open(self.data, self.days[1])
        self.assertEqual(ledger.trades, [])
        self.assertEqual(ledger.cash, 100)
        self.assertEqual(ledger.fees, 0)

    def test_sale_finances_buys_with_real_cost(self):
        self.data.by_day[self.days[1]]["B"] = [100, 100, 1_000_000]
        ledger = Ledger(cash=0, shares={"A": 10}, pending=order(self.days[0], 1000, B=1))
        ledger.execute_open(self.data, self.days[1])
        self.assertNotIn("A", ledger.shares)
        self.assertEqual(ledger.shares["B"], 9)
        self.assertAlmostEqual(ledger.cash, 97.15)
        self.assertEqual([r["side"] for r in ledger.trades], ["SELL", "BUY"])

    def test_missing_buy_cancelled_no_replacement(self):
        ledger = Ledger(cash=1000, pending=order(self.days[0], 1000, MISSING=1))
        ledger.execute_open(self.data, self.days[1])
        self.assertEqual(ledger.cash, 1000)
        self.assertEqual(ledger.shares, {})
        self.assertEqual(ledger.trades[0]["side"], "BUY_CANCELLED_NO_OPEN")

    def test_past_corporate_action_does_not_block_a_reused_ticker(self):
        for kind in ("cash", "stock"):
            with self.subTest(kind=kind):
                data = MemoryData(self.days, [{"A": [100, 100, 1_000_000]} for _ in self.days])
                if kind == "cash":
                    data.cash_actions = {"A": {"effective_date": "2023-01-01", "cash_per_share": 10}}
                else:
                    data.stock_actions = {"A": {"effective_date": "2023-01-01", "successor_ticker": "OLD", "shares_per_share": 1}}
                ledger = Ledger(cash=1000, pending=order(self.days[0], 1000, A=.5))
                ledger.execute_open(data, self.days[1])
                self.assertEqual(ledger.shares, {"A": 5})

    def test_missing_sell_and_held_close_block(self):
        ledger = Ledger(cash=0, shares={"MISSING": 10}, pending=order(self.days[0], 1000))
        with self.assertRaises(DataBlocked):
            ledger.execute_open(self.data, self.days[1])
        with self.assertRaises(DataBlocked):
            ledger.close_value(self.data, self.days[1])

    def test_split_changes_shares_not_nav_or_prior_signal(self):
        self.data.splits = [{"ticker": "A", "execution_date": self.days[1],
                             "split_from": 1, "split_to": 2}]
        self.data.by_day[self.days[1]]["A"] = [50, 50, 2_000_000]
        ledger = Ledger(cash=0, shares={"A": 10})
        ledger.events_before_open(self.data, self.days[1])
        self.assertEqual(ledger.shares["A"], 20)
        self.assertEqual(ledger.close_value(self.data, self.days[1])[0], 1000)
        self.assertEqual(adjusted_history(self.data, self.days[0], "A", 1), [100])
        self.assertEqual(adjusted_history(self.data, self.days[1], "A", 2), [50, 50])

    def test_dividend_entitlement_before_open_only_spendable_on_pay_date(self):
        self.data.dividends = [{"ticker": "A", "ex_dividend_date": self.days[1],
                                "pay_date": self.days[2], "cash_amount": 2,
                                "currency": "USD", "split_adjusted_cash_amount": .02}]
        ledger = Ledger(cash=0, shares={"A": 10})
        ledger.events_before_open(self.data, self.days[1])
        self.assertEqual(ledger.cash, 0)
        self.assertEqual(ledger.close_value(self.data, self.days[1])[2], 20)
        ledger.events_before_open(self.data, self.days[2])
        self.assertEqual(ledger.cash, 20)
        self.assertEqual(ledger.receivables, [])
        newcomer = Ledger(cash=1000, pending=order(self.days[0], 1000, A=1))
        newcomer.events_before_open(self.data, self.days[1])
        newcomer.execute_open(self.data, self.days[1])
        self.assertEqual(newcomer.receivables, [])

    def test_unknown_dividend_currency_blocks_instead_of_inventing_cash(self):
        self.data.dividends = [{"ticker": "A", "ex_dividend_date": self.days[1],
                                "pay_date": self.days[2], "cash_amount": 2, "currency": "CAD"}]
        ledger = Ledger(cash=0, shares={"A": 10})
        with self.assertRaises(DataBlocked):
            ledger.events_before_open(self.data, self.days[1])

    def test_cash_merger_claim_not_spent_without_settlement_date(self):
        self.data.cash_actions = {"A": {"effective_date": self.days[1], "cash_per_share": 110}}
        ledger = Ledger(cash=0, shares={"A": 10})
        ledger.events_before_open(self.data, self.days[1])
        self.assertEqual(ledger.shares, {})
        self.assertEqual(ledger.cash, 0)
        self.assertEqual(ledger.close_value(self.data, self.days[1])[0], 1100)

    def test_fusn_contingent_right_is_preserved_without_inventing_three_dollars(self):
        day = "2024-06-04"
        data = MemoryData([day], [{}], cash_actions=CoreData.cash_actions)
        ledger = Ledger(cash=0, shares={"FUSN": 10})
        ledger.events_before_open(data, day)
        self.assertEqual(ledger.shares, {})
        self.assertEqual(ledger.cash, 0)
        self.assertEqual(ledger.close_value(data, day)[0], 210)
        right = next(r for r in ledger.receivables if r["reason"] == "CONTINGENT_VALUE_RIGHT_UNPRICED")
        self.assertEqual(right["maximum_amount"], 30)
        self.assertEqual(right["amount"], 0)

    def test_stock_exchange_preserves_economic_interest(self):
        self.data.stock_actions = {"A": {"effective_date": self.days[1],
                                         "successor_ticker": "B", "shares_per_share": 1.436}}
        self.data.by_day[self.days[1]]["B"] = [100 / 1.436, 100 / 1.436, 1_000_000]
        ledger = Ledger(cash=0, shares={"A": 10})
        ledger.events_before_open(self.data, self.days[1])
        self.assertAlmostEqual(ledger.shares["B"], 14.36)
        self.assertAlmostEqual(ledger.close_value(self.data, self.days[1])[0], 1000)

    def test_brea_rename_keeps_shares_and_uses_successor_quote(self):
        day = "2025-10-03"
        data = MemoryData([day], [{"SLMT": [25, 26, 1_000_000]}],
                          stock_actions=CoreData.stock_actions)
        ledger = Ledger(cash=0, shares={"BREA": 10})
        ledger.events_before_open(data, day)
        self.assertEqual(ledger.shares, {"SLMT": 10})
        self.assertEqual(ledger.close_value(data, day)[0], 260)

    def test_mfh_rename_preserves_share_count(self):
        day = "2025-11-13"
        data = MemoryData([day], [{"CD": [11, 12, 1_000_000]}],
                          stock_actions=CoreData.stock_actions)
        ledger = Ledger(cash=0, shares={"MFH": 10})
        ledger.events_before_open(data, day)
        self.assertEqual(ledger.shares, {"CD": 10})
        self.assertEqual(ledger.close_value(data, day)[0], 120)

    def test_daily_gate_sells_next_open_and_no_10_percent_stock_stop(self):
        ledger = Ledger(cash=0, shares={"A": 10}, previous_risk=True, selection_month="2024-01")
        self.data.by_day[self.days[0]]["A"][1] = 80
        with patch("momentum_core.risk_on", return_value=True):
            ledger.step(self.data, self.days[0])
        self.assertIsNone(ledger.pending)
        with patch("momentum_core.risk_on", return_value=False):
            ledger.step(self.data, self.days[1])
        self.assertEqual(ledger.shares, {"A": 10})
        self.assertEqual(ledger.pending["targets"], [])
        with patch("momentum_core.risk_on", return_value=False):
            ledger.step(self.data, self.days[2])
        self.assertEqual(ledger.shares, {})


class EvidenceTests(unittest.TestCase):
    def test_saved_inputs_replay_without_a_client_or_calendar_request(self):
        days = long_data().days
        day = days[-1]
        rows = [{"ticker": f"S{k}", "name": f"Company {k}", "type": "CS",
                 "active": True, "primary_exchange": "XNYS"} for k in range(1000)]
        prices = {f"S{k}": [100, 101, 100_000] for k in range(1000)}
        prices["SPY"] = [400, 401, 1_000_000]
        client = unittest.mock.Mock()
        client._get.return_value = {"status": "OK", "results": []}
        with tempfile.TemporaryDirectory() as directory:
            with patch("momentum_core_data.fetch_spy_trading_calendar", return_value=days):
                online = CoreData(client, day, day, directory)
            for stamp in days[-2:]:
                atomic_json(Path(directory) / "raw-v1" / f"{stamp}.json.gz",
                            {"basis": "RAW", "version": 1, "date": stamp, "bars": prices})
            atomic_json(Path(directory) / "universe-v1" / f"{day}.json.gz",
                        {"basis": "PIT_REFERENCE_V1", "date": day, "records": rows})
            expected = online.history(day, "SPY", 2)
            online.universe(day)
            forbidden = unittest.mock.Mock()
            forbidden._get.side_effect = AssertionError("Offline must not call an API")
            with patch("momentum_core_data.fetch_spy_trading_calendar", side_effect=AssertionError("No calendar API")):
                offline = CoreData(forbidden, day, day, directory, offline=True)
                self.assertEqual(offline.history(day, "SPY", 2), expected)
                self.assertEqual(offline.universe(day), rows)
                self.assertEqual(online.input_fingerprint(), offline.input_fingerprint())
            forbidden._get.assert_not_called()
            (Path(directory) / "universe-v1" / f"{day}.json.gz").unlink()
            with self.assertRaisesRegex(DataBlocked, "Offline input missing: universe"):
                offline.universe(day)

    def test_offline_cannot_substitute_a_new_calendar_for_missing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(DataBlocked, "Offline input missing"):
                CoreData(None, "2024-01-01", "2026-09-01", directory, offline=True)

    def test_actual_imgn_merger_resolves_the_observed_missing_close(self):
        data = MemoryData(["2024-02-09", "2024-02-12"],
                          [{"IMGN": [31.2, 31.2, 100_000]}, {}],
                          cash_actions=CoreData.cash_actions)
        ledger = Ledger(cash=0, shares={"IMGN": 10})
        ledger.events_before_open(data, "2024-02-12")
        self.assertEqual(ledger.shares, {})
        self.assertAlmostEqual(ledger.close_value(data, "2024-02-12")[0], 312.6)
        self.assertEqual(ledger.cash, 0)

    def test_verified_cash_mergers_do_not_invent_market_fills_or_payment_dates(self):
        cases = [("AMAM", "2024-03-07", 28.0), ("HARP", "2024-03-11", 23.0),
                 ("ALPN", "2024-05-20", 65.0), ("LBPH", "2024-12-02", 60.0),
                 ("SLNO", "2026-05-18", 53.0)]
        for ticker, day, consideration in cases:
            with self.subTest(ticker=ticker):
                data = MemoryData([day], [{}], cash_actions=CoreData.cash_actions)
                ledger = Ledger(cash=0, shares={ticker: 10})
                ledger.events_before_open(data, day)
                self.assertAlmostEqual(ledger.close_value(data, day)[0], 10 * consideration)
                self.assertEqual(ledger.cash, 0)
                self.assertEqual(ledger.fees, 0)
                self.assertIsNone(ledger.receivables[0]["pay_date"])

    def test_resumed_base_and_stress_match_complete_replay(self):
        data = long_data()
        sessions = data.days[-45:]
        data.first_is_month_boundary = lambda: False
        data.sessions = sessions
        full, full_benchmark, _, _ = replay(data)
        stress_config = replace(CONFIG, one_way_cost=.003)
        full_stress, full_stress_benchmark, _, _ = replay(data, stress_config)
        data.sessions = sessions[:22]
        first, benchmark, _, _ = replay(data)
        stress, stress_benchmark, _, _ = replay(data, stress_config)
        checkpoint = {"strategy": first.to_dict(), "benchmark": benchmark.to_dict(),
                      "stress_strategy": stress.to_dict(), "stress_benchmark": stress_benchmark.to_dict()}
        frozen = json.dumps(checkpoint, sort_keys=True)
        data.sessions = sessions[22:]
        resumed, resumed_benchmark, _, _ = resume_paper(data, checkpoint)
        resumed_stress, resumed_stress_benchmark, _, _ = resume_paper(data, checkpoint, stress_config, stress=True)
        self.assertEqual(full.to_dict(), resumed.to_dict())
        self.assertEqual(full_benchmark.to_dict(), resumed_benchmark.to_dict())
        self.assertEqual(full_stress.to_dict(), resumed_stress.to_dict())
        self.assertEqual(full_stress_benchmark.to_dict(), resumed_stress_benchmark.to_dict())
        self.assertEqual(frozen, json.dumps(checkpoint, sort_keys=True))

    def test_paper_runner_resumes_four_ledgers_and_blocks_lost_original_record(self):
        data = long_data(2026)
        first_day = data.days[-1]
        self.assertEqual(first_day, "2026-10-27")
        data.first_is_month_boundary = lambda: False
        data.used_inputs = {"fixture": "synthetic; not performance evidence"}
        data.input_fingerprint = lambda: "synthetic-fixture"
        data.sessions = [first_day]
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"POLYGON_API_KEY": "fixture-key"}), \
                 patch("run_momentum_core.CoreData", return_value=data) as factory, \
                 patch("run_momentum_core.date") as clock_date, \
                 patch("run_momentum_core.datetime") as clock, patch("builtins.print"):
                clock_date.today.return_value = date(2026, 10, 28)
                clock_date.fromisoformat.side_effect = date.fromisoformat
                clock.now.return_value = datetime(2026, 10, 28, 6, 30, tzinfo=timezone.utc)
                initial = run(first_day, first_day, directory, directory, "paper")
                self.assertEqual(initial["status"], "PAPER_COLLECTING")
                path = Path(directory) / "Momentum_core_paper_checkpoint.json"
                old = json.loads(path.read_text())
                data.days.append("2026-10-28")
                data.by_day["2026-10-28"] = {ticker: list(bar) for ticker, bar in data.by_day[first_day].items()}
                data.sessions = ["2026-10-28"]
                data.first_is_month_boundary = lambda: self.fail("Resuming must not restart replay")
                clock_date.today.return_value = date(2026, 10, 29)
                clock.now.return_value = datetime(2026, 10, 29, 6, 30, tzinfo=timezone.utc)
                updated = run(first_day, "2026-10-28", directory, directory, "paper")
                new = json.loads(path.read_text())
                self.assertEqual(factory.call_args.args[1], "2026-10-28")
                self.assertEqual(new["strategy"]["equity"][:1], old["strategy"]["equity"])
                self.assertGreater(updated["metrics"]["ActualFees_USD"], 0)
                self.assertGreater(updated["double_cost_metrics"]["ActualFees_USD"],
                                   updated["metrics"]["ActualFees_USD"])
                self.assertFalse(updated["live_approved"])
                path.unlink()
                factory.reset_mock()
                with self.assertRaisesRegex(DataBlocked, "retrospective paper reconstruction forbidden"):
                    run(first_day, "2026-10-28", directory, directory, "paper")
                factory.assert_not_called()

    def test_clipped_vendor_history_blocks_instead_of_moving_start_forward(self):
        client = unittest.mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            with patch("momentum_core_data.fetch_spy_trading_calendar",
                       return_value=["2024-10-28", "2024-10-29", "2024-10-30"]):
                with self.assertRaisesRegex(DataBlocked, "prior sessions=0"):
                    CoreData(client, "2024-01-01", "2026-09-01", directory)
        client._get.assert_not_called()

    def test_batch_replay_equals_serialized_daily_paper_ledger(self):
        data = long_data()
        data.sessions = data.days[-45:]
        data.first_is_month_boundary = lambda: False
        batch, benchmark, result, _ = replay(data)
        paper = Ledger()
        halfway = len(data.sessions) // 2
        for day in data.sessions[:halfway]:
            paper.step(data, day)
        old = json.loads(json.dumps(paper.to_dict()))
        paper = Ledger(**json.loads(json.dumps(old)))
        for day in data.sessions[halfway:]:
            paper.step(data, day)
        self.assertEqual(paper.to_dict(), batch.to_dict())
        self.assertGreater(len(batch.trades), 0)
        self.assertTrue(math.isfinite(result["TotalReturn_pct"]))
        self.assertEqual(len(benchmark.equity), len(batch.equity))
        verify_forward_prefix(batch, old, data.sessions[-1])
        old["equity"][0]["nav"] += 1
        with self.assertRaisesRegex(DataBlocked, "historical revision"):
            verify_forward_prefix(batch, old, data.sessions[-1])

    def test_first_paper_session_records_next_open_intentions_without_invented_returns(self):
        data = long_data()
        data.sessions = data.days[-1:]
        data.first_is_month_boundary = lambda: False
        ledger, _, result, _ = replay(data)
        self.assertEqual(ledger.trades, [])
        self.assertTrue(ledger.pending["targets"])
        self.assertEqual(result["Periods"], 0)
        self.assertEqual(result["TotalReturn_pct"], 0)
        self.assertFalse(gates(result)[0]["pass"])

    def test_gate_boundary_and_nan_cannot_pass(self):
        values = {"Periods": 30, "TotalReturn_pct": 1, "SPYTotalReturn_pct": 0,
                  "TotalEdgeVsSPY_pct": 1, "DailyMaxDrawdown_pct": -20,
                  "PeriodHitRate_pct": 50}
        self.assertTrue(all(r["pass"] for r in gates(values)))
        values["TotalReturn_pct"] = float("nan")
        self.assertFalse(gates(values)[1]["pass"])

    def test_daily_drawdown_not_only_month_boundaries(self):
        strategy, benchmark = Ledger(), Ledger()
        days = ["2024-01-02", "2024-01-03", "2024-02-01", "2024-03-01"]
        strategy.equity = [{"date": d, "nav": v} for d, v in zip(days, [100, 70, 110, 121])]
        benchmark.equity = [{"date": d, "nav": 100} for d in days]
        strategy.first_is_month_boundary = True
        result, periods = metrics(strategy, benchmark)
        self.assertAlmostEqual(result["DailyMaxDrawdown_pct"], -30)
        self.assertEqual(result["Periods"], 2)
        self.assertEqual(len(periods), 2)

    def test_pagination_uses_every_page_and_strips_apikey(self):
        client = unittest.mock.Mock()
        client._get.side_effect = [
            {"results": [1], "next_url": "https://api.polygon.io/stocks/v1/splits?cursor=abc&apiKey=secret"},
            {"results": [2]}]
        self.assertEqual(paginate(client, "/stocks/v1/splits", {}), [1, 2])
        self.assertEqual(client._get.call_args_list[1].args[1], {"cursor": "abc"})

    def test_failed_run_invalidates_old_success_and_redacts_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Momentum_core_decision.json"
            path.write_text('{"status":"PAPER_ONLY"}')
            with patch.dict(os.environ, {"POLYGON_API_KEY": "secret-key"}):
                with patch("run_momentum_core.CoreData", side_effect=RuntimeError("apiKey=secret-key")):
                    with self.assertRaises(DataBlocked):
                        run("2024-01-01", "2024-01-31", directory, directory)
            record = json.loads(path.read_text())
            self.assertEqual(record["status"], "DATA_BLOCKED")
            self.assertFalse(record["live_approved"])
            self.assertNotIn("secret-key", path.read_text())
            orders = json.loads((Path(directory) / "Momentum_core_paper_orders.json").read_text())
            self.assertIsNone(orders["intentions_for_next_observed_session"])


if __name__ == "__main__":
    unittest.main()
