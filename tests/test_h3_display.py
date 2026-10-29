import copy
import unittest
from datetime import datetime,timezone
from h3_display import build,FP,basis_and_trades,rate_on


class DisplayTests(unittest.TestCase):
    def test_waiting_shows_a_budget_but_never_a_fabricated_return(self):
        source={'source_fingerprint':FP,'as_of':None,'source_run':'test','checkpoint_sha256':'test','account':None,'benchmark':None,'latest_decision':None}
        result=build(source,{}, {},{}, {},datetime(2026,10,29,tzinfo=timezone.utc))
        self.assertEqual(result['start_capital_sek'],100000);self.assertIsNone(result['metrics'])
        self.assertEqual(result['curve'],[]);self.assertEqual(result['trades'],[])

    def test_fx_and_spy_use_same_anchor_missing_rates_do_not_become_one(self):
        a={'cash':0.,'shares':{'SPY':100},'fees':15.,'receivables':[],'pending':None,'targets':[],
           'last_date':'2026-10-30','trades':[{'date':'2026-10-30','signal_date':'2026-10-29','ticker':'SPY','side':'BUY','quantity':100,'price':999.85,'fee':15.}],
           'equity':[{'date':'2026-10-29','nav':100000.},{'date':'2026-10-30','nav':110000.,'stock_value':110000.}]}
        source={'source_fingerprint':FP,'as_of':a['last_date'],'source_run':'test','checkpoint_sha256':'test','account':a,'benchmark':copy.deepcopy(a),'holdings':[{'ticker':'SPY','mark_usd':1100.}],'latest_decision':None,'splits':[]}
        result=build(source,{}, {'2026-10-29':10.,'2026-10-30':11.},{'SPY':{'usd':1100.,'session':'2026-10-30','mode':'CLOSE'}},{},datetime(2026,10,30,tzinfo=timezone.utc))
        self.assertAlmostEqual(result['metrics']['nav_sek'],121000.)
        self.assertAlmostEqual(result['metrics']['spy_nav_sek'],121000.)
        self.assertAlmostEqual(result['positions'][0]['quantity'],10.)
        self.assertEqual(result['trades'][0]['at'],'2026-10-30T13:30:00+00:00')
        blocked=build(source,{}, {},{}, {},datetime(2026,10,30,tzinfo=timezone.utc))
        self.assertEqual(blocked['status'],'FX_MISSING');self.assertIsNone(blocked['metrics'])
        self.assertIsNone(rate_on({'2026-10-01':10},'2026-10-30'))

    def test_split_preserves_cost_partial_sale_preserves_average_and_source_is_untouched(self):
        account={'trades':[{'date':'2026-10-29','ticker':'X','side':'BUY','quantity':10,'price':100,'fee':1.5},
                           {'date':'2026-11-02','ticker':'X','side':'SELL','quantity':5,'price':60,'fee':.45}]}
        original=copy.deepcopy(account)
        basis,trades=basis_and_trades(account,[{'execution_date':'2026-10-30','ticker':'X','split_to':2,'split_from':1}],{'2026-10-28':10,'2026-10-30':11},.1)
        self.assertEqual(account,original);self.assertEqual(basis['X']['quantity'],15)
        self.assertAlmostEqual(basis['X']['usd']/15,50.075)
        self.assertEqual(trades[1]['at'],'2026-11-02T14:30:00+00:00')
        self.assertAlmostEqual(trades[0]['fee_usd'],.15)
