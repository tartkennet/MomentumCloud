"""Synthetic accounting cases, never historical fills or strategy returns."""
import unittest

from audit_capital_availability import replay_cash_availability


def event(id, day, kind, **fields):
    return dict(id=id, at=day + "T13:30:00Z", kind=kind, source="SYNTHETIC_TEST_ONLY", **fields)


class CapitalAvailabilityTests(unittest.TestCase):
    def buy(self, id="buy", day="2023-04-03", lot="held", amount="100", **extra):
        return event(id, day, "BUY", lot_id=lot, amount=amount, currency="USD", **extra)

    def exit(self, day="2023-05-03", amount="40", currency="USD"):
        return event("exit", day, "EXIT", lot_id="held", receivable_id="claim", amount=amount, currency=currency)

    def test_late_exit_cannot_fund_next_rebalance(self):
        with self.assertRaisesRegex(ValueError, "Unavailable USD"):
            replay_cash_availability({"USD": "100"}, [self.buy(planned_exit="2023-05-01"), self.buy("rebalance", "2023-05-01", "new"), self.exit()])

    def test_trade_is_not_cash_receipt(self):
        with self.assertRaisesRegex(ValueError, "Unavailable USD"):
            replay_cash_availability({"USD": "100"}, [self.buy(), self.exit(), self.buy("rebalance", "2023-05-03", "new", "40")])

    def test_receipt_releases_actual_cash_once(self):
        events = [self.buy(), self.exit(), event("cash", "2023-05-05", "RECEIVE", receivable_id="claim"), self.buy("new", "2023-05-05", "new", "40")]
        result = replay_cash_availability({"USD": "100"}, events)
        self.assertEqual(result["journal"][-1]["available_cash"], {"USD": "0"})
        self.assertEqual(result["unreceived_claim_count"], 0)
        self.assertEqual(result["open_lot_count"], 1)

    def test_cad_receipt_cannot_fund_usd_buy(self):
        with self.assertRaisesRegex(ValueError, "Unavailable USD"):
            replay_cash_availability({"USD": "100"}, [self.buy(), self.exit(currency="CAD"), event("cash", "2023-05-05", "RECEIVE", receivable_id="claim"), self.buy("new", "2023-05-05", "new", "1")])

    def test_explicit_fx_cash_legs(self):
        events = [self.buy(), self.exit(currency="CAD"), event("cash", "2023-05-05", "RECEIVE", receivable_id="claim"), event("fx", "2023-05-05", "FX", currency="CAD", amount="40", receive_currency="USD", receive_amount="30")]
        r = replay_cash_availability({"USD": "100"}, events)
        self.assertEqual(r["journal"][-1]["available_cash"], {"CAD": "0", "USD": "30"})

    def test_unreceived_claim_remains_locked(self):
        r = replay_cash_availability({"USD": "100"}, [self.buy(), self.exit()])
        self.assertEqual(r["unreceived_claim_count"], 1)
        self.assertEqual(r["journal"][-1]["available_cash"], {"USD": "0"})

    def test_missing_exit_does_not_erase_loser(self):
        r = replay_cash_availability({"USD": "110"}, [self.buy(planned_exit="2023-05-01"), event("fee", "2023-05-02", "FEE", amount="1", currency="USD")])
        self.assertEqual(r["journal"][-1]["overdue_open_lots"], ["held"])
        self.assertEqual(r["journal"][-1]["open_lots"]["held"]["cost"], "100")
        self.assertNotIn("nav", r)

    def test_backdated_receipt_rejected(self):
        with self.assertRaisesRegex(ValueError, "no backdating"):
            replay_cash_availability({"USD": "100"}, [self.buy(), self.exit(), event("cash", "2023-05-01", "RECEIVE", receivable_id="claim")])

    def test_same_timestamp_does_not_move_later_receipt_before_buy(self):
        with self.assertRaisesRegex(ValueError, "Unavailable USD"):
            replay_cash_availability({"USD": "100"}, [self.buy(), self.exit(), self.buy("new", "2023-05-05", "new", "40"), event("cash", "2023-05-05", "RECEIVE", receivable_id="claim")])

    def test_zero_receipt_is_explicit_not_default(self):
        r = replay_cash_availability({"USD": "100"}, [self.buy(), self.exit(amount="0"), event("cash", "2023-05-05", "RECEIVE", receivable_id="claim")])
        self.assertEqual(r["unreceived_claim_count"], 0)
        self.assertEqual(r["journal"][-1]["available_cash"], {"USD": "0"})

    def test_double_receipt_rejected(self):
        with self.assertRaisesRegex(ValueError, "outstanding receivable"):
            replay_cash_availability({"USD": "100"}, [self.buy(), self.exit(), event("cash", "2023-05-05", "RECEIVE", receivable_id="claim"), event("again", "2023-05-05", "RECEIVE", receivable_id="claim")])

    def test_decimal_conservation_with_fee(self):
        r = replay_cash_availability({"USD": "0.3"}, [event("fee", "2023-05-01", "FEE", currency="USD", amount="0.1"), event("fee2", "2023-05-01", "FEE", currency="USD", amount="0.2")])
        self.assertEqual(r["journal"][-1]["available_cash"], {"USD": "0.0"})

    def test_nonfinite_negative_and_zero_debits_rejected(self):
        for value in ["NaN", "Infinity", "-1", "0"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                replay_cash_availability({"USD": "100"}, [self.buy(amount=value)])

    def test_source_and_timezone_required(self):
        for field, value in [("source", ""), ("at", "2023-04-03T13:30:00")]:
            e = self.buy(); e[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                replay_cash_availability({"USD": "100"}, [e])

    def test_duplicate_lot_event_or_claim_rejected(self):
        cases = [[self.buy(), self.buy()], [self.buy(), self.buy("other")], [self.buy(), self.exit(), self.buy("other", "2023-05-04", "other", "1"), event("exit2", "2023-05-04", "EXIT", lot_id="other", receivable_id="claim", currency="USD", amount="1")]]
        for events in cases:
            with self.subTest(events=events), self.assertRaises(ValueError):
                replay_cash_availability({"USD": "200"}, events)


if __name__ == "__main__":
    unittest.main()
