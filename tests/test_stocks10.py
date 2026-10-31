import unittest
from dataclasses import replace
from unittest.mock import patch
from types import SimpleNamespace

from momentum_core import CONFIG
from research_stocks10 import Stocks10Ledger, fee, select, APGE_COMPLETION
from run_stocks10_research import prior_fx
from audit_stocks10 import audit


class Stocks10Tests(unittest.TestCase):
    def data(self, opening=10):
        return SimpleNamespace(cash_actions={}, stock_actions={},
            bars=lambda day: {f'S{i}': [opening, opening, 10000] for i in range(10)})

    def ledger(self, cash):
        return Stocks10Ledger(cash=cash, pending={'signal_date': '2026-10-29', 'signal_nav': cash,
                     'targets': [{'ticker': f'S{i}', 'weight': .1} for i in range(10)]})

    def test_minimum_lots_reserved_before_other_buys(self):
        s = self.ledger(105)
        # USD1 minimum fee for EACH order makes ten USD10 lots unaffordable.
        s.execute_open(self.data(), '2026-10-30')
        self.assertEqual(s.cash, 105)
        self.assertEqual(s.trades, [])
        self.assertEqual(s.blocked[0]['reason'], 'TEN_MINIMUM_LOTS_UNAFFORDABLE')

    def test_whole_funded_basket_and_no_fund(self):
        s = self.ledger(205)
        s.execute_open(self.data(), '2026-10-30')
        self.assertEqual(len(s.shares), 10)
        self.assertTrue(all(q >= 1 and float(q).is_integer() for q in s.shares.values()))
        self.assertGreaterEqual(s.cash, 0)
        self.assertAlmostEqual(s.cash + sum(t['quantity'] * t['price'] + t['fee'] for t in s.trades), 205)

    def test_missing_open_does_not_partially_sell(self):
        s = self.ledger(200)
        s.shares = {'OLD': 2}
        s.execute_open(self.data(), '2026-10-30')
        self.assertEqual(s.shares, {'OLD': 2})
        self.assertFalse(s.trades)

    def test_fresh_rule_and_affordability(self):
        rows = [dict(ticker=f'S{i}', raw_price=10, return_1m=.1, return_3m=.1) for i in range(12)]
        rows[0]['return_1m'] = -.1
        rows[1]['raw_price'] = 100
        with patch('research_stocks10.population', return_value=rows):
            chosen, count = select(None, '2026-10-29', 200, True, .0015, {})
        self.assertEqual(count, 10)
        self.assertEqual(chosen[0]['ticker'], 'S2')
        self.assertAlmostEqual(sum(r['weight'] for r in chosen), 1)

    def test_signal_never_fills_itself(self):
        with self.assertRaises(ValueError):
            self.ledger(200).execute_open(self.data(), '2026-10-29')

    def test_fx_does_not_use_same_day_fix(self):
        self.assertEqual(prior_fx({'2026-10-29': 10., '2026-10-30': 99.}, '2026-10-30')['usdsek'], 10.)
        with self.assertRaises(Exception):
            prior_fx({'2026-10-01': 10.}, '2026-10-30')

    def test_fee_minimum_and_stress(self):
        self.assertAlmostEqual(fee(10), 1.04)
        self.assertAlmostEqual(fee(1000), 6.5)
        self.assertGreater(fee(1000, .003), fee(1000))

    def test_verified_cash_merger_is_unpaid_claim_not_fake_close(self):
        data = self.data()
        data.cash_actions = {'APGE': APGE_COMPLETION}
        data.splits = []; data.dividends = []; data.distributions = []
        s = Stocks10Ledger(cash=10, shares={'APGE': 2})
        s.events_before_open(data, '2026-09-03')
        self.assertNotIn('APGE', s.shares)
        self.assertEqual(s.cash, 10)
        self.assertAlmostEqual(s.receivables[0]['amount'], 270.22)
        self.assertIsNone(s.receivables[0]['pay_date'])

    def test_independent_accounting_rejects_tampered_fee_and_nav(self):
        data = self.data()
        data.source = data
        data.splits = []; data.dividends = []; data.distributions = []; data.halt_marks = {}
        s = self.ledger(205)
        s.execute_open(data, '2026-10-30')
        nav = s.cash + sum(s.shares.values()) * 10
        s.equity = [dict(date='2026-10-30', nav=nav, cash=s.cash, fees_cumulative=s.fees, positions=10)]
        config = replace(CONFIG, initial_cash=205)
        self.assertEqual(audit(data, config, s)['status'], 'PASS')
        s.trades[0]['fee'] += 1
        with self.assertRaises(AssertionError):
            audit(data, config, s)
        s.trades[0]['fee'] -= 1
        s.equity[0]['nav'] += 1
        with self.assertRaises(AssertionError):
            audit(data, config, s)

    def test_fractional_corporate_entitlement_does_not_lose_minimum_share(self):
        s = self.ledger(205)
        s.shares = {'S0': .5}
        s.execute_open(self.data(), '2026-10-30')
        self.assertGreaterEqual(s.shares['S0'], 1)
        self.assertGreaterEqual(s.cash, 0)
        self.assertTrue(all(float(t['quantity']).is_integer() for t in s.trades))


if __name__ == '__main__':
    unittest.main()
