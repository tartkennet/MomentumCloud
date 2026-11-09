import copy,json,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from best_v2_user import initialize,export,ACCOUNT
from audit_best_v2_user import audit_account
from quality_forward import digest
import best_v2_execution as execution
import best_v2_forward as controller

class UserStartTests(unittest.TestCase):
    def fixture(self):
        source=json.loads(Path('data/best-v2-user-start.json').read_text())
        rows=[dict(ticker=h['ticker'],cik=str(i+1).zfill(10),sector='S'+str(i),factor='F'+str(i),vol63=.3,cluster=h['ticker'],price_usd=h['mark_usd'],name=h['ticker'],instrument_type='CS',event_status='CLEAR') for i,h in enumerate(source['holdings'])]
        r=dict(signal=dict(selection=dict(rows=rows,month='2026-11'),quotes={h['ticker']:h['mark_usd'] for h in source['holdings']}),risk_on=True,price_as_of='2026-11-09',fx=dict(usdsek=source['fx_rate_sek_per_usd']),provenance={})
        now=datetime.fromisoformat('2026-11-09T22:30:00+00:00');s=initialize(source,r,now)
        execution.register(s,type('Data',(),{'sessions':['2026-11-09']})(),now)
        return s,r,now
    def test_exact_historical_positions_costs_nav_and_truthful_provenance(self):
        s,r,now=self.fixture();self.assertEqual(audit_account(s)['status'],'PASS')
        p=export(s,r,now)['paper'];self.assertEqual(p['account_id'],ACCOUNT)
        self.assertEqual(len(p['positions']),10);self.assertEqual(len(p['trades']),10)
        self.assertAlmostEqual(p['cash_sek'],350.94692180922357,places=6)
        self.assertAlmostEqual(p['nav_sek'],25337.65038799821,places=6)
        self.assertAlmostEqual(p['return_pct'],1.350601551992825,places=7)
        self.assertEqual(p['prospective_trade_count'],0);self.assertIsNone(p['first_trade_at'])
        figs=next(t for t in p['trades'] if t['ticker']=='FIGS');self.assertEqual(figs['quantity'],13);self.assertTrue(figs['original_limit_override'])
        self.assertTrue(all(t['execution_at'] is None and not t['actual_execution'] for t in p['trades']))
    def test_retry_and_tuesday_do_not_create_initial_order(self):
        s,r,now=self.fixture();before=copy.deepcopy(s['strategy'])
        for _ in range(3):controller.decide(s,r,None,datetime.fromisoformat('2026-11-10T14:52:00+00:00'))
        self.assertIsNone(s['pending']);self.assertEqual(s['strategy'],before);audit_account(s)
    def test_risk_off_plans_only_sales_and_preserves_seed(self):
        s,r,now=self.fixture();r['risk_on']=False;controller.decide(s,r,None,now)
        self.assertEqual(s['pending']['kind'],'RISK_OFF');self.assertTrue(all(o['side']=='SELL' for o in s['pending']['plan']['orders']))
        self.assertEqual(len(s['strategy']['trades']),10);audit_account(s)
    def test_december_retains_all_qualified_shares_no_double_buys(self):
        s,r,now=self.fixture();r['signal']['selection']['month']='2026-12';r['price_as_of']='2026-11-30'
        data=type('Data',(),{'bars':lambda self,day:{**{h['ticker']:[h['mark_usd'],h['mark_usd'],100] for h in s['source_start']['holdings']},'SPY':[600,600,100]}})()
        controller.decide(s,r,data,datetime.fromisoformat('2026-12-01T14:00:00+00:00'))
        self.assertIsNotNone(s['pending']);self.assertEqual(s['pending']['plan']['orders'],[])
        self.assertEqual(s['pending']['plan']['retained'],s['strategy']['shares'])
    def test_tampering_negative_cash_and_duplicate_ticker_fail_audit(self):
        s,r,now=self.fixture();s['strategy']['cash']+=1
        with self.assertRaises(AssertionError):audit_account(s)
        s,r,now=self.fixture();s['strategy']['trades'][0]['quantity']+=1
        with self.assertRaises(AssertionError):audit_account(s)
        source=copy.deepcopy(s['source_start']);source['holdings'][0]['quantity']=100000
        with self.assertRaises(AssertionError):audit_account(initialize(source,r,now))
