import itertools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_corrected_component_audit as audit

class ComponentAccountingTests(unittest.TestCase):
    def test_interaction_allocated_once(self):
        values={x:2*x[0]+3*x[1]+5*x[2]+7*x[0]*x[1] for x in itertools.product([False,True],repeat=3)}
        result=audit.factorial_contributions(values)
        self.assertAlmostEqual(result['stop_keeping_effect_pp'],5.5)
        self.assertAlmostEqual(result['regime_keeping_effect_pp'],6.5)
        self.assertAlmostEqual(result['extension_keeping_effect_pp'],5.0)
        self.assertAlmostEqual(result['all_rules_minus_none_pp'],17.0)

    def test_provider_snapshot_reuses_exact_response(self):
        calls=[]
        def fake(self,path,params=None):
            calls.append(path)
            return {'results':[{'close':len(calls)}]}
        with tempfile.TemporaryDirectory() as d,patch.object(audit,'SNAPSHOT',Path(d)),patch.object(audit.PolygonClient,'_get',fake):
            audit.freeze_provider()
            client=object.__new__(audit.PolygonClient)
            first=client._get('/test',{'date':'2023-01-01'})
            self.assertEqual(first,client._get('/test',{'date':'2023-01-01'}))
            self.assertEqual(len(calls),1)
            self.assertNotEqual(first,client._get('/test',{'date':'2023-01-02'}))

    def test_secret_removed_from_snapshot_pagination(self):
        value={'next_url':'https://api.example/test?cursor=abc&apiKey=secret','apiKey':'secret'}
        self.assertEqual(audit.redact_response(value),{'next_url':'https://api.example/test?cursor=abc'})

class NewGoldSettlementTests(unittest.TestCase):
    def test_converts_successor_market_price_at_planned_exit(self):
        engine=audit.engine
        cache={'2026-03-02':{'NGD':{'open':12.0}},'2026-04-01':{'CDE':{'open':20.0,'close':21.0,'high':22.0,'low':19.0}}}
        day,row,action=engine.resolve_exit_execution(cache,sorted(cache),'NGD','2026-04-01','2026-03-02','2026-04-01')
        self.assertEqual(day,'2026-04-01')
        self.assertAlmostEqual(row['open'],20.0*0.4959)
        self.assertAlmostEqual(row['close'],21.0*0.4959)
        self.assertEqual(action['valuation_ticker'],'CDE')

    def test_market_exit_before_merger_uses_ngd_price(self):
        engine=audit.engine
        cache={'2026-03-02':{'NGD':{'open':12.0}},'2026-03-10':{'NGD':{'open':11.0}},'2026-04-01':{'CDE':{'open':20.0}}}
        day,row,action=engine.resolve_exit_execution(cache,sorted(cache),'NGD','2026-03-10','2026-03-02','2026-04-01')
        self.assertEqual(day,'2026-03-10')
        self.assertEqual(row['open'],11.0)
        self.assertIsNone(action)
