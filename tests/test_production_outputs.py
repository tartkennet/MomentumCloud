import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from openpyxl import Workbook, load_workbook

from momentum_production import _signals, _write_workbook, fetch_security_master, validate_payload


class ProductionOutputTests(unittest.TestCase):
    def test_security_master_paginates_and_filters(self):
        class Client:
            def __init__(self):
                self.calls = 0

            def _get(self, path, params):
                self.calls += 1
                if self.calls == 1:
                    return {
                        "results": [
                            {"ticker": "GOOD", "name": "Good Inc", "type": "CS", "primary_exchange": "XNAS", "active": True},
                            {"ticker": "FUND", "name": "Fund", "type": "ETF", "primary_exchange": "XNAS", "active": True},
                        ],
                        "next_url": "https://api.polygon.io/v3/reference/tickers?cursor=two",
                    }
                return {"results": [
                    {"ticker": "SPAC", "name": "Example Acquisition Corp", "type": "CS", "primary_exchange": "XNYS", "active": True},
                    {"ticker": "OTHER", "name": "Other Inc", "type": "CS", "primary_exchange": "XNYS", "active": True},
                ]}

        client = Client()
        # The production cache is restored in CI; isolate this pagination unit test
        # so it exercises the client response rather than a prior workflow cache.
        with patch("momentum_production._load_cached_security_master", return_value={}), patch(
            "momentum_production._save_security_master_cache"
        ):
            self.assertEqual(sorted(fetch_security_master(client)), ["GOOD", "OTHER"])
        self.assertEqual(client.calls, 2)

    def test_risk_off_liquidates_and_never_buys(self):
        holdings = [{"ticker": "ABC", "stop_triggered": False}]
        target = [{"ticker": "XYZ", "rank": 1, "score": 99, "weight_pct": 100 / 15}]
        self.assertEqual(
            _signals(holdings, target, risk_on=False, rebalance_due=True),
            [{"ticker": "ABC", "action": "SELL", "reason": "RISK_OFF"}],
        )

    def test_monthly_rebalance_and_daily_stop(self):
        holdings = [
            {"ticker": "KEEP", "stop_triggered": False},
            {"ticker": "DROP", "stop_triggered": False},
            {"ticker": "STOP", "stop_triggered": True},
        ]
        target = [
            {"ticker": "KEEP", "rank": 1, "score": 99, "weight_pct": 100 / 15},
            {"ticker": "NEW", "rank": 2, "score": 98, "weight_pct": 100 / 15},
            {"ticker": "STOP", "rank": 3, "score": 97, "weight_pct": 100 / 15},
        ]
        signals = _signals(holdings, target, risk_on=True, rebalance_due=True)
        action = {row["ticker"]: (row["action"], row["reason"]) for row in signals}
        self.assertEqual(action["KEEP"], ("HOLD", "IN_PORTFOLIO"))
        self.assertEqual(action["DROP"], ("SELL", "MONTHLY_REBALANCE"))
        self.assertEqual(action["STOP"], ("SELL", "STOP_LOSS_10_PCT"))
        self.assertEqual(action["NEW"], ("BUY", "MONTHLY_REBALANCE"))

    def test_unfilled_monthly_buy_remains_actionable(self):
        target = [{
            "ticker": "NEW", "rank": 1, "target_rank": 1,
            "score": 99, "weight_pct": 100 / 15,
            "quantity": 3, "price_usd": 20,
        }]
        self.assertEqual(
            _signals([], target, risk_on=True, rebalance_due=False),
            [{
                "ticker": "NEW", "action": "BUY",
                "reason": "PENDING_MONTHLY_REBALANCE", "rank": 1,
                "target_rank": 1, "score": 99,
                "weight_pct": 100 / 15, "quantity": 3,
                "price_usd": 20,
            }],
        )

    def test_stopped_position_is_not_rebought_during_same_month(self):
        target = [{
            "ticker": "STOP", "rank": 1, "target_rank": 1,
            "score": 99, "weight_pct": 100 / 15,
            "quantity": 3, "price_usd": 20,
        }]
        self.assertEqual(
            _signals(
                [], target, risk_on=True, rebalance_due=False,
                blocked_tickers={"STOP"},
            ),
            [],
        )

    def test_payload_guard_rejects_configuration_drift(self):
        target = [
            {
                "ticker": f"T{index}",
                "price_usd": 20.0,
                "adv20_usd": 6_000_000.0,
                "return_1m_pct": 5.0,
                "return_3m_pct": 10.0,
                "relative_1m_pct": 3.0,
                "relative_3m_pct": 6.0,
                "quantity": 1,
                "weight_pct": 100 / 15,
            }
            for index in range(15)
        ]
        payload = {
            "config": {
                "selection_model": "fresh-momentum-1-3m",
                "position_count": 15,
                "min_price_usd": 10.0,
                "min_adv20_usd": 5_000_000.0,
                "stop_loss_pct": 10.0,
            },
            "limitation": "Current limitation: survivorship bias",
            "risk": {"status": "RISK ON"},
            "buy_now": [],
            "target_portfolio": target,
            "candidates": [],
        }
        validate_payload(payload)
        payload["config"]["min_adv20_usd"] = 20_000_000.0
        with self.assertRaisesRegex(RuntimeError, "min_adv20_usd"):
            validate_payload(payload)

    def test_workbook_contract_also_handles_risk_off_empty_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "template.xlsx"
            output = Path(directory) / "output.xlsx"
            workbook = Workbook()
            workbook.active.title = "Universe"
            workbook.save(template)
            with patch("momentum_production.TEMPLATE_FILE", str(template)), patch(
                "momentum_production.OUTPUT_FILE", str(output)
            ):
                _write_workbook(
                    [], [], [], [], [],
                    {"status": "RISK OFF", "risk_on": False},
                    "2026-09-11",
                )
            generated = load_workbook(output, read_only=True)
            self.assertTrue({"BuyNow", "TargetPortfolio", "Kandidater", "Holdings", "Signals", "Diagnostics"}.issubset(generated.sheetnames))


if __name__ == "__main__":
    unittest.main()
