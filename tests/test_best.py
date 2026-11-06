import copy
import json
import math
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

import best_strategy as strategy
import best_capital as capital
import best_forward as controller
import audit_best as audit
import momentum_core as core
from quality_forward import digest
from avanza10_forward import observe_account,summarize
from quality_account_audit import audit_account


class Data:
    def __init__(self,count=130):
        self.days=[];d=datetime(2026,11,5)
        while len(self.days)<253:
            if d.weekday()<5:self.days.append(d.date().isoformat())
            d-=timedelta(days=1)
        self.days.reverse();self.sessions=self.days;self._history={};self.records=[]
        self.splits=[];self.dividends=[];self.cash_actions={};self.stock_actions={};self.distributions=[];self.splits_by_ticker={}
        for i in range(count+1):
            t='SPY' if i==count else 'T'+str(i)
            returns=np.random.default_rng(i+10).normal(.0015 if t!='SPY' else .0002,.005,252)
            prices=40*np.cumprod(np.r_[1,1+returns]);bars=[[float(x),float(x),2_000_000] for x in prices]
            self._history[t]=list(zip(self.days,bars))
            if t!='SPY':self.records.append(dict(ticker=t,cik=str(i+1),name=t,type='CS',primary_exchange='XNAS',active=True))
    def history(self,day,ticker,count):return list(reversed([r for r in self._history.get(ticker,[]) if r[0]<=day][-count:]))
    def bars(self,day):return {t:h[-1][1] for t,h in self._history.items()}
    def universe(self,day):return self.records
    def set_day(self,day):pass
    def native_usd(self,day,currency):return 1
    def input_fingerprint(self):return digest(self.records)


def formation():
    data=Data();rows,diag,on=strategy.collect_prices(data,'2026-11-05')
    pool=copy.deepcopy([r for r in rows if r['strong']][:40]);codes=['2011','3511','5011','7311','6011','4911','4511','5811']
    for i,r in enumerate(pool):
        r['sic']=codes[i%len(codes)];r['industry']=r['sic'][:2];r['division']=strategy.division(r['sic'])
    strategy.clusters(pool);targets,skips=strategy.select(pool)
    now=datetime.fromisoformat('2026-11-06T10:00:00+00:00')
    report=dict(ranked_liquid=rows,strong_pool=pool,targets=targets,diagnostics=diag,risk_on=True,
        generated_at=now.isoformat(),price_as_of='2026-11-05',fx=dict(date='2026-11-05',usdsek=10),provenance={'fixture':True},
        signal=dict(version=controller.VERSION,market_verified=True,selection_verified=True,quotes_as_of='2026-11-05',
                    selection=dict(month='2026-11',as_of='2026-11-05',rows=targets),quotes={r['ticker']:r['price_usd'] for r in targets}))
    return data,report,now


class BestTests(unittest.TestCase):
    def test_full_universe_price_rank_and_independent_formulas(self):
        data,r,now=formation()
        self.assertGreater(r['diagnostics']['priced_liquid'],100)
        self.assertFalse(r['diagnostics']['adv_truncation'])
        self.assertEqual(audit.population(data,'2026-11-05',r['ranked_liquid'])['status'],'PASS')
        with self.assertRaises(AssertionError):audit.population(data,'2026-11-05',r['ranked_liquid'][1:])
        self.assertEqual(len(r['targets']),10)
        self.assertEqual(audit.signal(r)['status'],'PASS')
        spy=core.adjusted_history(data,'2026-11-05','SPY',253)
        for row in r['ranked_liquid']:audit.price_metrics(row,core.adjusted_history(data,'2026-11-05',row['ticker'],253),spy)
        corrupted=copy.deepcopy(r);corrupted['ranked_liquid'][0]['score']+=.1
        with self.assertRaises(AssertionError):audit.signal(corrupted)

    def test_no_etf_no_spy_and_no_capital_selection(self):
        data,r,now=formation();original=[x['ticker'] for x in r['targets']]
        data.records.extend([dict(data.records[0],ticker='SPY'),dict(data.records[1],ticker='ETF',type='ETF')])
        rows,_,_=strategy.collect_prices(data,'2026-11-05')
        self.assertNotIn('SPY',[x['ticker'] for x in rows]);self.assertNotIn('ETF',[x['ticker'] for x in rows])
        minimum=capital.requirements(r['targets'],10)
        audit.funding(r['targets'],10,minimum)
        for amount in ['100','20000','1000000','AUTO_MINIMUM']:
            state=controller.initialize(r,now,amount)
            controller.decide(state,r,data,now)
            self.assertEqual([x['ticker'] for x in r['signal']['selection']['rows']],original)
            if amount=='100':self.assertIn('UNFUNDED_OR_RISK_LIMITED_MINIMUM_BASKET',state['blockers'])
            if state.get('pending'):
                self.assertEqual([x['ticker'] for x in state['pending']['targets']],original)
                self.assertTrue(all(type(o['quantity']) is int and o['quantity']>=1 for o in state['pending']['plan']['orders']))

    def test_browser_and_python_funding_agree_without_changing_names(self):
        import subprocess
        data,r,now=formation();r.update(delivery={'verified':True},operations={'delayed':False})
        minimum=capital.requirements(r['targets'],10)
        script="const p=require('./public/best-plan');const r=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(JSON.stringify([100,20000,1000000].map(capital=>{const x=p.plan(r,{capital,cash:capital},new Date('2026-11-06T10:00:00Z'));return {names:x.rows.map(r=>r.ticker),min:x.minimumCapital,total:x.minimumTotal};})));"
        out=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(r),text=True))
        for result in out:
            self.assertEqual(result['names'],[x['ticker'] for x in r['targets']])
            self.assertEqual(result['min'],minimum['minimum_capital_sek'])
            self.assertEqual(result['total'],minimum['minimum_one_each_sek'])

    def test_breadth_and_correlated_cluster_caps_are_not_relaxed(self):
        data,r,now=formation();pool=copy.deepcopy(r['strong_pool'])
        for row in pool:row['cluster']='ONE_RISK'
        chosen,skips=strategy.select(pool)
        self.assertEqual(chosen,[]);self.assertTrue(any(s['reason']=='CLUSTER_CAP' for s in skips))
        self.assertEqual(strategy.select(pool[:9])[0],[])

    def test_prices_have_no_future_split_or_history_information(self):
        data,r,now=formation();day='2026-11-05';t=data.records[0]['ticker']
        before=core.adjusted_history(data,day,t,253)
        data.splits_by_ticker[t]=[dict(ticker=t,execution_date='2026-11-06',split_from=1,split_to=5)]
        self.assertEqual(before,core.adjusted_history(data,day,t,253))
        date=data.days[200];data.splits_by_ticker[t]=[dict(ticker=t,execution_date=date,split_from=1,split_to=2)]
        after=core.adjusted_history(data,day,t,253)
        self.assertEqual(before[0],after[0]);self.assertEqual(before[-1]/2,after[-1])
        data._history[t].append(('2026-11-06',[99999,99999,99999]))
        self.assertEqual(after,core.adjusted_history(data,day,t,253))

    def test_prospective_fill_mark_costs_and_independent_account(self):
        data,r,now=formation();state=controller.initialize(r,now)
        controller.decide(state,r,data,now);self.assertFalse(state['strategy']['trades'])
        opening={t:[b[0],b[1],b[2]] for t,b in data.bars('2026-11-05').items()}
        client=SimpleNamespace(get=lambda *a,**k:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in opening.items()]})
        state=observe_account(state,data,client,datetime.fromisoformat('2026-11-06T14:52:00+00:00'))
        self.assertEqual(len(state['strategy']['shares']),10)
        self.assertEqual(audit_account(state,'strategy')['status'],'PASS')
        for t in state['strategy']['trades']:state['trade_fx'][t['date']]=dict(date=t['date'],usdsek=10)
        state['audits']={k:audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
        paper=summarize(state,r['signal'],now)
        self.assertTrue(paper['paper_started']);self.assertIsNone(paper['nav_sek'])
        self.assertEqual(audit.account(state,paper)['status'],'PASS')
        data.days.append('2026-11-06')
        for t,h in data._history.items():h.append(('2026-11-06',list(h[-1][1])))
        state=observe_account(state,data,client,datetime.fromisoformat('2026-11-09T08:22:00+00:00'))
        state['valuation_fx']['2026-11-06']=dict(date='2026-11-06',usdsek=10)
        paper=summarize(state,r['signal'],now)
        self.assertIsNotNone(paper['nav_sek']);self.assertEqual(len(paper['curve']),1)
        self.assertEqual(audit.account(state,paper)['status'],'PASS')
        altered=copy.deepcopy(paper);altered['nav_sek']+=1
        with self.assertRaises(AssertionError):audit.account(state,altered)
        old=copy.deepcopy(state)
        r['risk_on']=False;controller.decide(state,r,data,datetime.fromisoformat('2026-11-09T08:23:00+00:00'))
        self.assertEqual(state['pending']['kind'],'RISK_OFF')
        self.assertEqual(state['strategy']['trades'],old['strategy']['trades'])

    def test_partial_fill_is_explicitly_blocked_without_fake_tenth_holding(self):
        data,r,now=formation();state=controller.initialize(r,now);controller.decide(state,r,data,now)
        bad=state['pending']['plan']['orders'][0]['ticker']
        bars=data.bars('2026-11-05');quotes={t:list(b) for t,b in bars.items()};quotes[bad][0]*=5
        client=SimpleNamespace(get=lambda *a,**k:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in quotes.items()]})
        state=observe_account(state,data,client,datetime.fromisoformat('2026-11-06T14:52:00+00:00'))
        controller.decide(state,r,data,datetime.fromisoformat('2026-11-06T14:53:00+00:00'))
        self.assertEqual(len(state['strategy']['shares']),9)
        self.assertIn('PARTIAL_FILL_REVIEW_REQUIRED',state['blockers'])
        self.assertNotIn(bad,state['strategy']['shares'])
        self.assertEqual(audit_account(state,'strategy')['status'],'PASS')

    def test_same_day_late_plan_does_not_backfill_and_retention_has_no_round_trip(self):
        data,r,now=formation();late=datetime.fromisoformat('2026-11-06T15:00:00+00:00')
        state=controller.initialize(r,late);controller.decide(state,r,data,late)
        bars=data.bars('2026-11-05');client=SimpleNamespace(get=lambda *a,**k:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in bars.items()]})
        after=observe_account(state,data,client,late)
        self.assertFalse(after['strategy']['trades'])
        rows=r['targets'];shares={x['ticker']:1 for x in rows}
        p=capital.orders(rows,shares,100000,10000,{})
        self.assertEqual(p['orders'],[]);self.assertEqual(p['retained'],shares)
