import unittest
from types import SimpleNamespace
from research_momentum10_v3 import SelectionLedger


class CashCompletionTests(unittest.TestCase):
    def test_rapt_becomes_locked_cash_claim_not_invented_trade_or_quote(self):
        s=SelectionLedger(cash=20,shares={'RAPT':3})
        data=SimpleNamespace(splits=[],dividends=[],stock_actions={},distributions=[],
            cash_actions={'RAPT':dict(effective_date='2026-03-03',cash_per_share=58.,pay_date=None)})
        s.events_before_open(data,'2026-03-03')
        self.assertEqual(s.cash,20);self.assertNotIn('RAPT',s.shares)
        self.assertEqual(sum(c['amount'] for c in s.receivables),174)
        self.assertTrue(all(c['pay_date'] is None for c in s.receivables))
        self.assertFalse(any(t['side'] in ('BUY','SELL') for t in s.trades))
