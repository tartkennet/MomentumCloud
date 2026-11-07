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
        apparel=classify(dict(description='Healthcare apparel company designing and selling scrubwear through digital retail stores.',sic_code='2300'))
        self.assertEqual(apparel['sector'],'Consumer Discretionary');self.assertTrue(apparel['healthcare_exposure'])
        self.assertEqual(classify(dict(description='Software platform serving businesses globally through subscription services.',sic_code='7372'))['sector'],'Technology')
        self.assertEqual(classify(dict(description='The company operates a chain of grocery retail stores with food staples and household goods.',sic_code=None))['sector'],'Consumer Staples')
        with self.assertRaises(DataUnavailable):classify(dict(description='unknown',sic_code='7374'))

    def test_generic_cash_target_detection_and_acquirer_distinction(self):
        target='Under the definitive merger agreement each share of our common stock will be converted into the right to receive $53 in cash.'
        self.assertTrue(target_event(target));self.assertTrue(event_text(target))
        buyer='We acquired Example Ltd under a definitive merger agreement. We paid $53 million cash for its assets.'
        self.assertFalse(target_event(buyer))

    def test_sector_concentration_does_not_force_five_sectors(self):
        _,r,_=formation();p=copy.deepcopy(r['strong_pool'])
        for i,x in enumerate(p):x.update(sector='Healthcare',factor='Healthcare',cluster=x['ticker'])
        chosen,_=strategy.select(p)
        self.assertEqual(len(chosen),10)
        self.assertEqual([x['ticker'] for x in chosen],[x['ticker'] for x in p[:10]])
        req=capital.requirements(chosen,10);audit.funding(chosen,10,req)
        self.assertNotIn('sector',req['caps']);self.assertNotIn('factor',req['caps'])

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

class EarlyTurnTests(unittest.TestCase):
    def test_confirmed_turn_can_precede_sma200_recovery_without_ticker_rules(self):
        chronological=[100+1.3*math.sin(i*1.7) for i in range(80)]+[100-40*i/100+1.3*math.sin(i*1.7) for i in range(100)]+[60+30*i/72+1.3*math.sin(i*1.7) for i in range(73)]
        m=strategy.metrics(chronological[::-1],[100]*253,[2e8]*5+[1e8]*20)
        self.assertFalse(m['strong']);self.assertLess(m['sma50'],m['sma200']);self.assertTrue(m['early']['qualified'])
        thin=strategy.metrics(chronological[::-1],[100]*253,[1e8]*25)
        self.assertFalse(thin['early']['qualified']);self.assertIn('volume',thin['early']['failed'])

    def test_js_soft_sector_funding_agrees_with_real_financial_formula(self):
        import subprocess
        _,r,_=formation();r.update(delivery={'verified':True},operations={'delayed':False})
        script="const p=require('./public/best-v2-plan');const r=JSON.parse(require('fs').readFileSync(0,'utf8')); console.log(JSON.stringify([1,25000,1000000].map(capital=>{let x=p.plan(r,{capital,cash:capital},new Date('2026-11-06T10:00:00Z'));return {minimum:x.minimumCapital,names:x.rows.map(r=>r.ticker)};})));"
        out=json.loads(subprocess.check_output(['node','-e',script],text=True,input=json.dumps(r)))
        for x in out:
            self.assertEqual(x['minimum'],capital.requirements(r['targets'],10)['minimum_capital_sek'])
            self.assertEqual(x['names'],[r['ticker'] for r in r['targets']])

class MirrorTests(unittest.TestCase):
    def test_mirror_wrong_filing_and_missing_exhibits_are_not_accepted(self):
        from best_v2_mirrors import inspect_pdf
        from types import SimpleNamespace
        class Page:
            def extract_text(self):return 'FORM 6-K SHARKNINJA '+('business '*100)
        reader=SimpleNamespace(metadata={'/Title':'WRONG'},pages=[Page()]*71)
        e=dict(accession_number='ACTUAL',pages=71,markers=['FORM 6-K','Exhibit 99.4'])
        with patch('best_v2_mirrors.PdfReader',return_value=reader):
            with self.assertRaisesRegex(DataUnavailable,'MIRROR_ACCESSION_MISMATCH'):inspect_pdf(b'%PDF-FAKE',e)
            reader.metadata={'/Title':'ACTUAL'}
            with self.assertRaisesRegex(DataUnavailable,'MIRROR_IDENTITY_OR_EXHIBIT_MISMATCH'):inspect_pdf(b'%PDF-FAKE',e)

class FilingIdentityTests(unittest.TestCase):
    def test_reused_ticker_does_not_select_another_issuers_annual_report(self):
        def filing(cik,form,accession):return dict(type=form,filing_date='2026-10-01',accession_number=accession,source_url='https://www.sec.gov/example',main_file_url='https://api.polygon.io/v1/reference/sec/filings/'+accession+'/files/main.htm',entities=[dict(relation='filer',company_data={'cik':cik})])
        class Client:
            def get(self,path,params):
                if path.endswith('/index'):return {'results':[dict(cik='123',form_type='10-K',accession_number='RIGHT',filing_date='2026-10-01')]}
                if path.endswith('/text'):return {'results':[]}
                assert params['filing_date.lte']=='20261106'
                return {'results':[filing('123','10-K','RIGHT'),filing('999','20-F','WRONG')]}
        requested=[]
        with patch('best_v2_sources.raw_document',side_effect=lambda client,url:(requested.append(url) or b'Ordinary business operations with no price binding transaction.')):
            result=review_events(Client(),dict(ticker='ANY',cik='0000000123'),'2026-11-06')
        self.assertEqual(result['status'],'CLEAR');self.assertEqual(len(requested),1);self.assertIn('/RIGHT/',requested[0])

class OperationsTests(unittest.TestCase):
    def test_scheduler_must_be_enabled_on_default_branch_and_source_bound(self):
        import os
        from best_v2_operations import verify
        env=dict(GITHUB_REPOSITORY='owner/repo',GITHUB_REF='refs/heads/main',GITHUB_SHA='commit')
        paths=[]
        def response(args,**kw):
            path=args[-1];paths.append(path)
            return json.dumps({'default_branch':'main'} if path=='repos/owner/repo' else {'state':'active','id':123})
        with tempfile.TemporaryDirectory() as out,patch.dict(os.environ,env),patch('subprocess.check_output',side_effect=response):
            verify(out);proof=json.loads((Path(out)/'operations.json').read_text())
            self.assertTrue(proof['enabled']);self.assertEqual(proof['source_commit'],'commit');self.assertEqual(paths[0],'repos/owner/repo')
        with tempfile.TemporaryDirectory() as out,patch.dict(os.environ,env),patch('subprocess.check_output',return_value=json.dumps({'default_branch':'main','state':'disabled_manually','id':123})):
            with self.assertRaisesRegex(ValueError,'AUTOMATION_NOT_ENABLED'):verify(out)
            self.assertFalse((Path(out)/'operations.json').exists())

class EventContextTests(unittest.TestCase):
    def test_historical_completed_or_unrelated_stock_conversion_is_not_pending_target(self):
        past='Under the definitive merger agreement each share of our common stock were converted into the right to receive $53 in cash in 2021.'
        self.assertFalse(target_event(past))
        distant='We acquired another company under a definitive merger agreement. '+('Unrelated business operations. '*100)+' Each share of our common stock will be converted into a right to receive cash.'
        self.assertFalse(target_event(distant))


class OriginalBundleTests(unittest.TestCase):
    def test_complete_pinned_bundle_requires_every_narrative_and_unchanged_bytes(self):
        import hashlib
        from best_v2_mirrors import bundle
        raw=b'<html>FORM 6-K Example Company SIGNATURES ordinary operations.</html>'
        digest=hashlib.sha256(raw).hexdigest()
        entry=dict(cik='0000000123',accession_number='0000000123-26-000001',filing_date='2026-11-06',form_type='6-K',original_index='https://www.sec.gov/index',
            required_documents=['main.htm','ex99.htm'],documents=[dict(name=n,url='https://cdn.yahoofinance.com/prod/sec-filings/0000000123/000000012326000001/'+n,sha256=digest,min_characters=20,markers=['Example Company'],required_items=[]) for n in ('main.htm','ex99.htm')])
        with tempfile.TemporaryDirectory() as root,patch('best_v2_mirrors.download',return_value=raw):
            text,receipt=bundle(entry,root,'https://www.sec.gov/submission.txt')
            self.assertEqual(len(receipt['documents']),2)
            entry['documents'].pop()
            with self.assertRaisesRegex(DataUnavailable,'INCOMPLETE_ORIGINAL_BUNDLE'):bundle(entry,root,'https://www.sec.gov/submission.txt')
        entry['required_documents']=['main.htm']
        with tempfile.TemporaryDirectory() as root,patch('best_v2_mirrors.download',return_value=raw+b'changed'):
            with self.assertRaisesRegex(DataUnavailable,'CHANGED_ISSUER_MIRROR'):bundle(entry,root,'https://www.sec.gov/submission.txt')


class ForeignAnnualTests(unittest.TestCase):
    def test_missing_legacy_foreign_annual_requires_indexed_original_and_amendment(self):
        filings=[dict(cik='123',form_type=f,accession_number=a,filing_date=d,filing_url='https://www.sec.gov/'+a+'.txt') for f,a,d in [('20-F','BASE','2026-04-02'),('20-F/A','AMENDMENT','2026-05-22')]]
        class Client:
            def get(self,path,params):return {'results':filings if path.endswith('/index') else []}
        calls=[]
        def original(row,filing,date):
            calls.append(filing['accession_number']);return 'Ordinary operations and complete original public disclosures.',{'source_url':filing['filing_url']}
        with patch('best_v2_sources.material_original',side_effect=original):result=review_events(Client(),dict(ticker='FOREIGN',cik='0000000123'),'2026-11-06')
        self.assertEqual(set(calls),{'BASE','AMENDMENT'});self.assertEqual(result['status'],'CLEAR')
        with patch('best_v2_sources.material_original',side_effect=DataUnavailable('ORIGINAL_MISSING')):
            with self.assertRaisesRegex(DataUnavailable,'ORIGINAL_MISSING'):review_events(Client(),dict(ticker='FOREIGN',cik='0000000123'),'2026-11-06')
