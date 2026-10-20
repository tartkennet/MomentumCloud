import contextlib
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

import backtest_momentum_v3 as backtest
from data_access_preflight import first_trading_day_on_or_after
from model_validation import evaluate_metrics, load_model_validation, validation_source_fingerprint
from momentum_config import PRODUCTION
from momentum_master_v3 import PolygonClient
from momentum_production import validate_payload
from momentum_strategy import rank_universe
import validate_production_backtest as validator


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


def metrics():
    return {
        "Periods": 30, "TotalReturn_pct": 10.0, "SPYTotalReturn_pct": 5.0,
        "TotalEdgeVsSPY_pct": 5.0, "DailyMaxDrawdown_pct": -20.0,
        "PeriodHitRate_pct": 50.0,
    }


def summary():
    return {
        **metrics(), "RebalanceMonths": 1, "TopN": 15,
        "SelectionModel": "v4-balanced", "LiquidityRule": "FIXED_MIN_ADV20_5M_USD",
        "EffectiveMinADV20_USD": 5_000_000.0, "EntryExecution": "next-open",
        "ExitExecution": "next-open", "RebalanceExitExecution": "next-open",
        "StopLoss_pct": 10.0, "Universe": "POINT_IN_TIME_US_COMMON_STOCKS",
    }


class ValidationIntegrityTests(unittest.TestCase):
    def test_provider_missing_open_stays_missing_until_execution_rejects_it(self):
        client = PolygonClient("test")
        client._get = Mock(return_value={"results": [{"T": "GAP", "c": 100.0, "v": 1000.0}]})
        row = client.fetch_grouped_stocks("2024-02-01")["GAP"]
        self.assertIsNone(row["open"])
        with self.assertRaisesRegex(RuntimeError, "Missing open"):
            backtest.execution_price(row, "next-open", ticker="GAP")

    def test_split_fetch_reads_all_pages_without_forwarding_url_credentials(self):
        client = PolygonClient("test")
        client._get = Mock(side_effect=[
            {"results": [{"ticker": "A"}], "next_url": "https://api.polygon.io/stocks/v1/splits?cursor=second&apiKey=do-not-forward"},
            {"results": [{"ticker": "B"}]},
        ])
        self.assertEqual([row["ticker"] for row in client.fetch_recent_splits("2024-01-01", "2026-09-01")], ["A", "B"])
        self.assertEqual(client._get.call_args.args[1], {"cursor": "second"})

    def test_old_cache_with_possible_fabricated_opens_is_discarded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.json"
            path.write_text(json.dumps({"version": 3, "sessions": {},
                                        "adjusted_through": "2026-09-01", "universe_signature": "scope"}))
            self.assertEqual(backtest.load_backtest_cache(path, "scope"), ({}, None))

    def test_holiday_preflight_uses_actual_spy_calendar(self):
        client = Mock()
        client._get.return_value = {"results": [{"t": 1704153600000}]}
        self.assertEqual(first_trading_day_on_or_after(client, date(2024, 1, 1)), date(2024, 1, 2))
        self.assertIn("/SPY/range/", client._get.call_args.args[0])

    def test_empty_calendar_does_not_silently_guess_a_weekday(self):
        client = Mock()
        client._get.return_value = {"results": []}
        with self.assertRaisesRegex(RuntimeError, "No SPY sessions"):
            first_trading_day_on_or_after(client, date(2024, 1, 1))

    def test_existing_gate_boundaries_are_unchanged(self):
        self.assertTrue(all(evaluate_metrics(metrics()).values()))
        cases = (
            ("Periods", 29, "at_least_30_periods"),
            ("DailyMaxDrawdown_pct", -20.001, "daily_max_drawdown_at_most_20_pct"),
            ("PeriodHitRate_pct", 49.999, "hit_rate_at_least_50_pct"),
        )
        for field, value, gate in cases:
            with self.subTest(field=field):
                values = metrics()
                values[field] = value
                self.assertFalse(evaluate_metrics(values)[gate])
        values = {**metrics(), "TotalReturn_pct": 0.0, "TotalEdgeVsSPY_pct": -5.0}
        self.assertFalse(evaluate_metrics(values)["positive_net_return"])
        values = {**metrics(), "TotalReturn_pct": 5.0, "TotalEdgeVsSPY_pct": 0.0}
        self.assertFalse(evaluate_metrics(values)["beats_spy"])

    def test_nonfinite_metrics_cannot_be_approved(self):
        values = {**metrics(), "DailyMaxDrawdown_pct": float("nan")}
        with self.assertRaisesRegex(ValueError, "finite"):
            evaluate_metrics(values)

    def test_reported_edge_must_match_strategy_minus_spy(self):
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            evaluate_metrics({**metrics(), "TotalEdgeVsSPY_pct": 100.0})

    def test_failure_replaces_stale_go_with_error_and_clears_stale_results(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            Path("Momentum_validation_decision.json").write_text('{"status":"GO"}')
            Path("Momentum_backtest_summary.csv").write_text("stale")
            with patch.object(validator, "run", side_effect=RuntimeError("Missing ROVR exit")), patch(
                "sys.argv", ["validator", "--start", "2024-01-01", "--end", "2026-09-01"]
            ):
                with self.assertRaisesRegex(RuntimeError, "ROVR"):
                    validator.main()
            decision = json.loads(Path("Momentum_validation_decision.json").read_text())
            self.assertEqual(decision["status"], "VALIDATION_ERROR")
            self.assertEqual(decision["metrics"], {})
            self.assertFalse(Path("Momentum_backtest_summary.csv").exists())
            self.assertFalse(load_model_validation()["approved"])

    def test_completed_no_go_is_saved_with_each_actual_failed_gate(self):
        def fake_backtest(**kwargs):
            row = {**summary(), "TotalReturn_pct": -5.0, "TotalEdgeVsSPY_pct": -10.0}
            pd.DataFrame([row]).to_csv("Momentum_backtest_summary.csv", index=False)

        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            with patch.object(validator, "run", side_effect=fake_backtest), patch(
                "sys.argv", ["validator", "--start", "2024-01-01", "--end", "2026-09-01"]
            ):
                with self.assertRaisesRegex(RuntimeError, "positive_net_return, beats_spy"):
                    validator.main()
            decision = json.loads(Path("Momentum_validation_decision.json").read_text())
            self.assertEqual(decision["status"], "NO-GO")
            self.assertEqual(decision["metrics"]["TotalReturn_pct"], -5.0)
            self.assertFalse(decision["gates"]["positive_net_return"])
            self.assertFalse(decision["gates"]["beats_spy"])
            self.assertTrue(decision["gates"]["at_least_30_periods"])

    def test_writer_and_production_loader_agree_on_complete_go(self):
        def fake_backtest(**kwargs):
            pd.DataFrame([summary()]).to_csv("Momentum_backtest_summary.csv", index=False)

        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            with patch.object(validator, "run", side_effect=fake_backtest), patch(
                "sys.argv", ["validator", "--start", "2024-01-01", "--end", "2026-09-01"]
            ):
                validator.main()
            self.assertTrue(load_model_validation()["approved"])

    def test_stale_source_and_forged_true_flags_cannot_unlock_buys(self):
        valid = {
            "status": "GO", "model": "v4-balanced",
            "universe": "POINT_IN_TIME_US_COMMON_STOCKS",
            "metrics": metrics(), "gates": evaluate_metrics(metrics()),
            "source_fingerprint": validation_source_fingerprint(),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decision.json"
            for changed in (
                {"source_fingerprint": "old-source"},
                {"metrics": {**metrics(), "PeriodHitRate_pct": 20.0}},
                {"metrics": {}},
            ):
                with self.subTest(changed=changed):
                    path.write_text(json.dumps({**valid, **changed}))
                    loaded = load_model_validation(path)
                    self.assertFalse(loaded["approved"])
                    self.assertEqual(loaded["status"], "UNVALIDATED")

    def test_non_object_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decision.json"
            path.write_text("[]")
            self.assertFalse(load_model_validation(path)["approved"])

    def test_rovr_settles_at_verified_cash_and_values_as_cash_thereafter(self):
        days = ["2024-02-26", "2024-02-27", "2024-03-01"]
        cache = {"2024-02-26": {"ROVR": {"open": 10.99, "close": 10.99}}}
        day, row, action = backtest.resolve_exit_execution(
            cache, days, "ROVR", "2024-03-01", "2024-02-01", "2024-03-01"
        )
        self.assertEqual((day, row["close"]), ("2024-02-27", 11.0))
        self.assertEqual(action["reason"], "CASH_MERGER")
        self.assertEqual(backtest.position_close_on_day(cache, "ROVR", "2024-02-28")[0], 11.0)

    def test_unknown_delisting_is_not_given_an_invented_cash_exit(self):
        self.assertEqual(
            backtest.resolve_exit_execution({}, ["2024-03-01"], "UNKNOWN", "2024-03-01", "2024-02-01", "2024-03-01"),
            (None, None, None),
        )

    def test_missing_daily_price_cannot_manufacture_a_low_drawdown(self):
        positions = [{
            "SignalDate": "2024-01-31", "EntryDate": "2024-02-01",
            "PlannedExitDate": "2024-02-05", "ExitDate": "2024-02-05",
            "Ticker": "GAP", "EntryPrice_USD": 100.0, "ExitPrice_USD": 90.0,
        }]
        cache = {"2024-02-01": {"GAP": {"close": 100.0}}, "2024-02-02": {}, "2024-02-05": {}}
        with self.assertRaisesRegex(RuntimeError, "Missing daily valuation"):
            backtest.daily_portfolio_max_drawdown(positions, cache, sorted(cache))

    def test_v4_backtest_uses_live_ranking_and_tie_break(self):
        closes = [150.0 - 50.0 * i / 252.0 for i in range(253)]
        history = [
            (f"session-{i}", {
                "SPY": {"close": 160.0 - 60.0 * i / 252.0, "volume": 1e6},
                "Z": {"close": close, "volume": 1e6},
                "A": {"close": close, "volume": 1e6},
            })
            for i, close in enumerate(closes)
        ]
        expected = rank_universe(["Z", "A"], history)
        with patch.object(backtest, "session_window", return_value=history), patch.object(
            backtest, "core_market_regime_is_risk_on", return_value=True
        ):
            selected = backtest.choose_top(
                None, {"2024-01-31": history[0][1]}, ["Z", "A"], "2024-01-31",
                top_n=2, selection_model="v4-balanced",
            )
        self.assertEqual([p.ticker for p in selected], [p.ticker for p in expected])
        self.assertEqual(selected[0].ticker, "A")
        self.assertEqual([p.total_score for p in selected], [p.score for p in expected])

    def test_valid_v4_target_is_not_rejected_for_short_term_relative_weakness(self):
        payload = {
            "config": PRODUCTION.to_dict(), "limitation": PRODUCTION.limitation,
            "model_validation": {"approved": True, "status": "APPROVED", "gates": evaluate_metrics(metrics())},
            "risk": {"status": "RISK ON"}, "buy_now": [], "candidates": [],
            "target_portfolio": [
                {"ticker": str(i), "price_usd": 20.0, "adv20_usd": 6e6,
                 "quantity": 1, "weight_pct": 100 / 15,
                 "return_1m_pct": -1.0, "return_3m_pct": -2.0,
                 "relative_1m_pct": -3.0, "relative_3m_pct": -4.0}
                for i in range(15)
            ],
        }
        validate_payload(payload)

    def test_future_bad_print_does_not_change_earlier_signal_universe(self):
        days = ["2024-01-31", "2024-02-01", "2024-02-29", "2024-03-01",
                "2024-03-28", "2024-04-01", "2024-04-30", "2024-05-01"]
        cache = {day: {ticker: {"open": 100.0, "close": 100.0, "volume": 1e6}
                       for ticker in ("GOOD", "LATER_BAD", "SPY")} for day in days}
        seen = {}
        def choose(client, prices, tickers, signal, *args):
            seen[signal] = list(tickers)
            return [SimpleNamespace(ticker="GOOD", price_usd=100.0, total_score=100.0)]
        client = Mock()
        client.fetch_recent_splits.return_value = []
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ, {"POLYGON_API_KEY": "test"}))
                stack.enter_context(patch.object(backtest, "PolygonClient", return_value=client))
                stack.enter_context(patch.object(backtest, "fetch_spy_trading_calendar", return_value=days))
                stack.enter_context(patch.object(backtest, "load_backtest_cache", return_value=(cache, "9999-12-31")))
                stack.enter_context(patch.object(backtest, "save_backtest_cache"))
                stack.enter_context(patch.object(backtest, "point_in_time_universes",
                    return_value={d: ["GOOD", "LATER_BAD"] for d in days}))
                stack.enter_context(patch.object(backtest, "find_unverified_split_basis_tickers",
                    return_value={"LATER_BAD": ["2024-02-15: bad print"]}))
                stack.enter_context(patch.object(backtest, "choose_top", side_effect=choose))
                backtest.run("2024-01-01", "2024-05-01", 1, top_n=1,
                             selection_model="v4-balanced", entry_execution="next-open",
                             rebalance_exit_execution="next-open")
        self.assertIn("LATER_BAD", seen["2024-01-31"])
        self.assertNotIn("LATER_BAD", seen["2024-02-29"])


if __name__ == "__main__":
    unittest.main()

