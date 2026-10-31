import unittest
from dataclasses import replace
from unittest.mock import patch
from types import SimpleNamespace

from momentum_core import CONFIG
from research_stocks10 import Stocks10Ledger, fee, select
from run_stocks10_research import prior_fx


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


if __name__ == '__main__':
    unittest.main()
