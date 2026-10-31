import unittest
from types import SimpleNamespace
from research_momentum10_v2 import RetentionLedger
from research_momentum10_fx import TD_REPAIR
from audit_momentum10_v2 import native_account
from dataclasses import replace
from momentum_core import CONFIG


class NativeDividendTests(unittest.TestCase):
    def test_native_claim_revalues_and_only_funds_cash_on_payment(self):
        rates={'2026-01-09':.72,'2026-01-12':.70,'2026-02-02':.73,'2026-02-03':.99}
        d=SimpleNamespace(splits=[],dividends=[dict(TD_REPAIR)],cash_actions={},stock_actions={},distributions=[],
                          native_usd=lambda day,currency:rates[day])
        s=RetentionLedger(cash=10,shares={'TD':2},stop_mode='fixed10',
                          references={'TD':dict(reference=100,level=90,distance=.1)})
        s.events_before_open(d,'2026-01-09')
        self.assertEqual(s.cash,10);self.assertEqual(s.receivables[0]['currency'],'CAD')
        self.assertAlmostEqual(s.receivables[0]['native_amount'],2.16)
        self.assertAlmostEqual(s.receivables[0]['amount'],2.16*.72)
        d.dividends=[];s.events_before_open(d,'2026-01-12')
        self.assertEqual(s.cash,10);self.assertAlmostEqual(s.receivables[0]['amount'],2.16*.70)
        self.assertAlmostEqual(s.references['TD']['level'],90-1.08*.70)
        s.events_before_open(d,'2026-02-02')
        self.assertFalse(s.receivables)
        self.assertAlmostEqual(s.cash,10+2.16*.73*(1-.0025))
        self.assertAlmostEqual(s.fees,2.16*.73*.0025)
        old=s.references['TD']['level'];s.events_before_open(d,'2026-02-03')
        self.assertAlmostEqual(s.references['TD']['level'],old)
        self.assertEqual(len(s.fx_payments),1)

    def test_native_claim_cannot_become_usd_one_for_one(self):
        d=SimpleNamespace(splits=[],dividends=[dict(TD_REPAIR)],cash_actions={},stock_actions={},distributions=[],
                          native_usd=lambda day,currency:.5)
        s=RetentionLedger(cash=0,shares={'TD':1})
        s.events_before_open(d,'2026-01-09')
        self.assertAlmostEqual(s.receivables[0]['amount'],.54)
        self.assertEqual(s.cash,0)

    def test_independent_native_account_rejects_wrong_nav_or_payment(self):
        rates={'2026-01-08':.72,'2026-01-09':.72,'2026-01-12':.70,'2026-02-02':.73}
        d=SimpleNamespace(splits=[],dividends=[],cash_actions={},stock_actions={},distributions=[],halt_marks={},
            native_usd=lambda day,currency:rates[day],bars=lambda day:{'TD':[100,100,10000]})
        d.source=SimpleNamespace(splits=[],dividends=[dict(TD_REPAIR)])
        s=RetentionLedger(cash=1000)
        config=replace(CONFIG,initial_cash=1000)
        for day in rates:
            d.dividends=[dict(TD_REPAIR)] if day=='2026-01-09' else []
            s.events_before_open(d,day)
            if day=='2026-01-08':s._trade(day,'2026-01-07','TD','BUY',2,100,config,'MEMBERSHIP_ENTRY')
            nav,stock,claims=s.close_value(d,day)
            s.equity.append(dict(date=day,nav=nav,cash=s.cash,stock_value=stock,receivables=claims,
                                 fees_cumulative=s.fees,positions=len(s.shares)))
        fx=lambda day,currency:rates[day] if currency=='CAD' else 1.
        self.assertEqual(native_account(d,config,s,fx)['status'],'PASS')
        s.equity[1]['nav']+=1
        with self.assertRaises(AssertionError):native_account(d,config,s,fx)
        s.equity[1]['nav']-=1;s.fx_payments[0]['gross_usd']+=1
        with self.assertRaises(AssertionError):native_account(d,config,s,fx)
