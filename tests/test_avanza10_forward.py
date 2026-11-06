import copy
import math
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from avanza10_forward import POLICY, decide, membership, summarize, run, observe_account
from quality_forward import bootstrap, digest
from quality_strategy import division, rank
from quality_account_audit import audit_account
from run_quality_forward import observe
import test_quality_earnings as fixtures
from test_quality_forward import Data


def fixture(capital=20000):
    now=datetime.fromisoformat('2026-11-02T08:17:00+00:00')
    rows=rank(fixtures.QualityTests().rows())
    for r in rows:r['division']=division(r['sic'])
    snap=dict(version='avanza10-paper-v2',market_verified=True,selection_verified=True,coverage=.90,
              quotes_as_of='2026-10-30',quotes={r['ticker']:20 for r in rows},
              selection=dict(month='2026-11',rows=rows))
    report=dict(generated_at=now.isoformat(),price_as_of='2026-10-30',risk_on=True,errors=[],status='OK')
    state=bootstrap(dict(initial_usd=capital/10,fx=dict(date='2026-10-30',usdsek=10)),digest(POLICY),now)
    state.update(initial_sek=capital,opening_quotes=[],valuation_fx={},trade_fx={},ranked_targets=[])
    bars={r['ticker']:[19,20,100000] for r in rows};bars['SPY']=[300,303,1000000]
    data=Data(['2026-10-30'],bars)
    client=SimpleNamespace(get=lambda *args,**kwargs:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in bars.items()]})
    return state,report,snap,data,client,now


class AvanzaAccountTests(unittest.TestCase):
    def test_close_before_actual_account_initialization_is_never_a_start_mark(self):
        s,r,a,d,c,now=fixture()
        s['initialized_at']='2026-11-02T21:30:00+00:00'
        s['event_through']='2026-11-02'
        result=observe_account(s,Data(['2026-10-30','2026-11-02'],d._bars),c,
                               datetime.fromisoformat('2026-11-03T08:17:00+00:00'))
        self.assertFalse(result['strategy']['equity'])
        self.assertFalse(result['valuation_quotes'])

    def test_commit_observe_value_audit_and_no_mutation_of_prior(self):
        s,r,a,d,c,now=fixture();decide(s,r,a,d,now)
        self.assertEqual(len(s['pending']['targets']),10)
        self.assertFalse(s['strategy']['trades'])
        prior=copy.deepcopy(s)
        s=observe(s,d,c,datetime.fromisoformat('2026-11-02T14:47:00+00:00'))
        self.assertFalse(prior['strategy']['trades'])
        self.assertEqual(len(s['strategy']['shares']),10)
        self.assertEqual(audit_account(s,'strategy')['status'],'PASS')
        for t in s['strategy']['trades']:s['trade_fx'][t['date']]=dict(usdsek=10,date=t['date'])
        s['audits']={k:audit_account(s,k,k=='benchmark') for k in ('strategy','benchmark')}
        self.assertTrue(summarize(s,a,now)['valuation_pending'])
        self.assertIsNone(summarize(s,a,now)['nav_sek'])
        s=observe(s,Data(['2026-10-30','2026-11-02'],d._bars),c,datetime.fromisoformat('2026-11-03T08:17:00+00:00'))
        s['valuation_fx']['2026-11-02']=dict(usdsek=10,date='2026-11-02')
        result=summarize(s,a,now)
        expected=s['strategy']['cash']*10+sum(q*20*10 for q in s['strategy']['shares'].values())
        self.assertAlmostEqual(result['nav_sek'],expected)
        self.assertAlmostEqual(result['return_sek'],expected-20000)
        self.assertAlmostEqual(result['costs_sek'],sum(t['fee']*10 for t in s['strategy']['trades']))
        self.assertEqual(len(result['positions']),10)
        self.assertTrue(result['benchmark_valid'])
        self.assertEqual(result['rebalances'],1)
        from audit_avanza10 import check
        self.assertEqual(check(s,result)['status'],'PASS')
        altered=copy.deepcopy(result);altered['return_sek']+=1
        with self.assertRaises(AssertionError):check(s,altered)
        bad=copy.deepcopy(s);bad['strategy']['cash']+=1
        with self.assertRaises(AssertionError):audit_account(bad,'strategy')

    def test_small_capital_does_not_replace_expensive_names_or_create_plan(self):
        s,r,a,d,c,now=fixture(500)
        names=[x['ticker'] for x in membership(a['selection']['rows'])]
        decide(s,r,a,d,now)
        self.assertEqual([x['ticker'] for x in s['ranked_targets']],names)
        self.assertIsNone(s['pending']);self.assertFalse(s['strategy']['trades'])
        self.assertIn('UNFUNDED_OR_RISK_LIMITED_MINIMUM_BASKET',s['blockers'])

    def test_risk_off_cancels_buys_and_bad_coverage_never_executes(self):
        s,r,a,d,c,now=fixture();decide(s,r,a,d,now);history=copy.deepcopy(s['decisions'])
        decide(s,dict(r,risk_on=False),a,d,now)
        self.assertIsNone(s['pending']);self.assertEqual(s['decisions'],history)
        s,r,a,d,c,now=fixture();decide(s,r,a,d,now)
        decide(s,r,dict(a,coverage=.89),d,now)
        self.assertIsNone(s['pending']);self.assertTrue(s['blockers'])

    def test_monthly_retention_keeps_qualifying_quantities(self):
        s,r,a,d,c,now=fixture();decide(s,r,a,d,now)
        s=observe(s,d,c,datetime.fromisoformat('2026-11-02T14:47:00+00:00'))
        shares=copy.deepcopy(s['strategy']['shares'])
        later=datetime.fromisoformat('2026-12-01T08:17:00+00:00')
        r.update(generated_at=later.isoformat(),price_as_of='2026-11-30')
        a.update(quotes_as_of='2026-11-30');a['selection']['month']='2026-12'
        decide(s,r,a,d,later)
        self.assertEqual(s['pending']['plan']['retained'],shares)
        self.assertEqual(s['pending']['plan']['orders'],[])

    def test_missed_open_is_recorded_without_backfill(self):
        s,r,a,d,c,now=fixture();decide(s,r,a,d,now)
        later=datetime.fromisoformat('2026-11-03T08:17:00+00:00')
        s=observe(s,Data(['2026-10-30','2026-11-02'],d._bars),c,later)
        self.assertFalse(s['strategy']['trades']);self.assertIsNone(s['pending'])
        self.assertTrue(any(g['kind']=='MISSED_OPEN_NO_BACKFILL' for g in s['gaps']))

    def test_partial_fill_cannot_be_called_active_or_completed_rebalance(self):
        s,r,a,d,c,now=fixture();decide(s,r,a,d,now)
        missing=s['pending']['plan']['orders'][0]['ticker'];d._bars[missing][0]=500
        s=observe(s,d,c,datetime.fromisoformat('2026-11-02T14:47:00+00:00'))
        decide(s,r,a,d,now)
        self.assertIn('PARTIAL_FILL_REVIEW_REQUIRED',s['blockers'])
        for t in s['strategy']['trades']:s['trade_fx'][t['date']]=dict(usdsek=10,date=t['date'])
        s['audits']={}
        self.assertEqual(summarize(s,a,now)['rebalances'],0)
        self.assertEqual(summarize(s,a,now)['status'],'BLOCKED')


if __name__=='__main__':unittest.main()
