import json
import math
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from momentum_core import (
    CONFIG, DataBlocked, Ledger, adjusted_history, capped_weights, gates,
    metrics, risk_on, select_targets,
)
from momentum_core_data import paginate
from run_momentum_core import run


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


def long_data():
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(300)]
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

    def test_stock_exchange_preserves_economic_interest(self):
        self.data.stock_actions = {"A": {"effective_date": self.days[1],
                                         "successor_ticker": "B", "shares_per_share": 1.436}}
        self.data.by_day[self.days[1]]["B"] = [100 / 1.436, 100 / 1.436, 1_000_000]
        ledger = Ledger(cash=0, shares={"A": 10})
        ledger.events_before_open(self.data, self.days[1])
        self.assertAlmostEqual(ledger.shares["B"], 14.36)
        self.assertAlmostEqual(ledger.close_value(self.data, self.days[1])[0], 1000)

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


if __name__ == "__main__":
    unittest.main()
