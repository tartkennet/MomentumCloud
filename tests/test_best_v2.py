import copy,json,math,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import numpy as np
from test_best import Data
import best_v2_strategy as strategy
import best_v2_capital as capital
import best_v2_forward as controller
import audit_best_v2 as audit
from best_v2_sources import classify,event_text,target_event,review_events
from quality_sources import DataUnavailable
from quality_forward import digest
from avanza10_forward import observe_account,summarize
from quality_account_audit import audit_account


def formation():
    data=Data(180);rows,diag,on=strategy.collect_prices(data,'2026-11-05')
    pool=copy.deepcopy([r for r in rows if r['strong']][:60]);sectors=['Healthcare','Technology','Industrials','Energy','Consumer Staples','Consumer Discretionary','Financials','Materials']
    for i,r in enumerate(pool):r.update(sector=sectors[i%8],factor=sectors[i%8],event_status='CLEAR')
    strategy.clusters(pool);targets,skips=strategy.select(pool)
    assert len(targets)==10
    now=datetime.fromisoformat('2026-11-06T10:00:00+00:00')
    report=dict(model=strategy.MODEL,ranked_liquid=rows,strong_pool=pool,targets=targets,diagnostics=diag,risk_on=True,
      generated_at=now.isoformat(),price_as_of='2026-11-05',fx=dict(date='2026-11-05',usdsek=10),provenance={'fixture':True},
      signal=dict(version=controller.VERSION,market_verified=True,selection_verified=True,quotes_as_of='2026-11-05',
       selection=dict(month='2026-11',as_of='2026-11-05',rows=targets),quotes={r['ticker']:r['price_usd'] for r in targets}))
    return data,report,now

class V2Tests(unittest.TestCase):
    def test_complete_population_and_independent_new_metrics(self):
        data,r,_=formation();self.assertGreater(len(r['ranked_liquid']),100)
        audit.population(data,'2026-11-05',r['ranked_liquid']);audit.signal(r)
        spy=[b[1] for _,b in data.history('2026-11-05','SPY',253)]
        for row in r['ranked_liquid']:
            h=data.history('2026-11-05',row['ticker'],253)
            audit.price_metrics(row,[b[1] for _,b in h],spy,[b[1]*b[2] for _,b in h[:25]])
        broken=copy.deepcopy(r);broken['ranked_liquid'][0]['score']+=.01
        with self.assertRaises(AssertionError):audit.signal(broken)

    def test_cash_peg_is_not_momentum_and_volatility_floor_applies(self):
        spy=[100/(1.0001**i) for i in range(253)]
        c=[100*(1+.00005*math.sin(i)) for i in range(80)]+[80/(1.001**i) for i in range(173)]
        m=strategy.metrics(c,spy,[1e8]*25)
        self.assertFalse(m['strong']);self.assertIn('ABNORMALLY_LOW_VOLATILITY',m['price_exclusions'])
        self.assertIn('PRICE_PINNING',m['price_exclusions']);self.assertLessEqual(m['risk_adjusted'],m['momentum_6_1']/.2+1e-10)

    def test_parabolic_jump_is_explicitly_rejected(self):
        c=[200]+[100/(1.001**i) for i in range(252)]
        m=strategy.metrics(c,[100]*253,[1e8]*25)
        self.assertFalse(m['strong']);self.assertIn('UNRESOLVED_ADJUSTED_PRICE_JUMP',m['price_exclusions']);self.assertIn('OVEREXTENDED',m['price_exclusions'])

    def test_economic_healthcare_overrides_software_sic_without_ticker_list(self):
        p=dict(description='Platform treating musculoskeletal conditions and improving member outcomes through software.',sic_code='7374')
        self.assertEqual(classify(p)['sector'],'Healthcare')
        self.assertEqual(classify(dict(description='Software platform serving businesses globally through subscription services.',sic_code='7372'))['sector'],'Technology')
        with self.assertRaises(DataUnavailable):classify(dict(description='unknown',sic_code='7374'))

    def test_generic_cash_target_detection_and_acquirer_distinction(self):
        target='Under the definitive merger agreement each share of our common stock will be converted into the right to receive $53 in cash.'
        self.assertTrue(target_event(target));self.assertTrue(event_text(target))
        buyer='We acquired Example Ltd under a definitive merger agreement. We paid $53 million cash for its assets.'
        self.assertFalse(target_event(buyer))

    def test_sectors_and_factors_cannot_be_relaxed_to_fill_ten(self):
        _,r,_=formation();p=copy.deepcopy(r['strong_pool'])
        for x in p:x['sector']='Healthcare'
        self.assertEqual(strategy.select(p)[0],[])
        self.assertEqual(len({x['sector'] for x in r['targets']}),8)
        self.assertTrue(all(sum(x['sector']==s for x in r['targets'])<=2 for s in {x['sector'] for x in r['targets']}))

    def test_target_capital_whole_lots_and_independent_finance(self):
        data,r,now=formation();original=[x['ticker'] for x in r['targets']]
        s=controller.initialize(r,now);self.assertGreaterEqual(s['initial_sek'],25000)
        controller.decide(s,r,data,now)
        self.assertTrue(any(o['quantity']>1 for o in s['pending']['plan']['orders']))
        audit.funding(r['targets'],10,s['capital_configuration']['funding'])
        audit.plan(r['targets'],s['pending']['plan'],{},s['initial_usd'],s['strategy']['cash'],{})
        for amount in ('1','25000','1000000'):
            q=controller.initialize(r,now,amount);controller.decide(q,r,data,now)
            self.assertEqual(original,[x['ticker'] for x in r['signal']['selection']['rows']])
            if amount=='1':self.assertTrue(q['blockers'])
        pricey=copy.deepcopy(r)
        for x in pricey['signal']['selection']['rows']:pricey['signal']['quotes'][x['ticker']]*=100
        self.assertGreater(controller.initialize(pricey,now)['initial_sek'],27000)

    def test_actual_future_fixture_observation_and_audited_bookkeeping(self):
        from types import SimpleNamespace
        data,r,now=formation();s=controller.initialize(r,now);controller.decide(s,r,data,now)
        client=SimpleNamespace(get=lambda *a,**k:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in data.bars('2026-11-05').items()]})
        self.assertEqual(s['strategy']['trades'],[])
        s=observe_account(s,data,client,datetime.fromisoformat('2026-11-06T14:52:00+00:00'))
        self.assertEqual(len(s['strategy']['shares']),10)
        for t in s['strategy']['trades']:s['trade_fx'][t['date']]=dict(date=t['date'],usdsek=10)
        s['audits']={k:audit_account(s,k,k=='benchmark') for k in ('strategy','benchmark')}
        p=summarize(s,r['signal'],now);audit.account(s,p)
        self.assertTrue(p['paper_started']);self.assertIsNone(p['nav_sek'])
        bad=copy.deepcopy(s);bad['strategy']['cash']+=1
        with self.assertRaises(AssertionError):audit.account(bad,p)

    def test_missing_event_text_is_not_a_clearance(self):
        class Client:
            def get(self,path,params):
                if path.endswith('/index'):return {'results':[dict(cik='123',form_type='8-K',accession_number='A',filing_date='2026-11-05')]}
                return {'results':[]}
        with self.assertRaisesRegex(DataUnavailable,'EVENT_TEXT_COVERAGE_GAP'):
            review_events(Client(),dict(ticker='NEW',cik='0000000123'),'2026-11-06')
