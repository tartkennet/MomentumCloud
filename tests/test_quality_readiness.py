import copy,unittest
from datetime import datetime
from types import SimpleNamespace
import test_quality_forward as fixtures
from run_quality_forward import decide,export
from quality_forward import process,digest


class FirstNovemberSession(unittest.TestCase):
    def test_new_month_invalidates_old_intention_when_fresh_source_gate_fails(self):
        s=fixtures.ControllerTests().state();before=copy.deepcopy(s['decisions'])
        decide(s,dict(risk_on=True,paper_start_permit=False,price_as_of='2026-10-30'),None,datetime.fromisoformat('2026-11-02T08:17:00+00:00'))
        self.assertIsNone(s['pending']);self.assertEqual(s['decisions'],before)
        self.assertEqual(s['cancelled_intentions'][0]['reason'],'NEW_MONTH_REQUIRES_FRESH_SELECTION')
        self.assertFalse(s['strategy']['trades'])

    def test_fresh_november_intention_is_not_a_completed_purchase(self):
        s=fixtures.ControllerTests().state();targets=copy.deepcopy(s['pending']['targets'])
        report=dict(risk_on=True,paper_start_permit=True,price_as_of='2026-10-30',targets=targets,fx=dict(date='2026-10-30',usdsek=10))
        d=SimpleNamespace(bars=lambda day:{'SPY':[300,300,1000000]})
        decide(s,report,d,datetime.fromisoformat('2026-11-02T08:17:00+00:00'))
        self.assertEqual(s['pending']['created_at'],'2026-11-02T08:17:00+00:00')
        self.assertEqual(len(s['decisions']),2);self.assertFalse(s['strategy']['shares'])
        s['audits']={}
        result=export(report,s,datetime.fromisoformat('2026-11-02T08:18:00+00:00'))
        self.assertFalse(result['paper_started']);self.assertFalse(result['positions']);self.assertFalse(result['trades']);self.assertIsNone(result['paper_metrics'])
        bars={o['ticker']:[19,20,10000] for o in s['pending']['plan']['orders']};bars['SPY']=[300,301,10000]
        before=process(s,{},datetime.fromisoformat('2026-11-02T14:29:00+00:00'),['2026-11-02'],bars)
        self.assertFalse(before['strategy']['trades'])
        after=process(s,{},datetime.fromisoformat('2026-11-02T14:47:00+00:00'),['2026-11-02'],bars)
        self.assertEqual(len(after['strategy']['shares']),10)
        self.assertTrue(all(t['execution_at']=='2026-11-02T14:30:00+00:00' for t in after['strategy']['trades']))




class CashOnlyReadiness(unittest.TestCase):
    def test_accepts_audited_cash_mark_without_inventing_a_fill(self):
        from run_quality_forward import fingerprint, observe
        from verify_quality_readiness import check
        s=fixtures.ControllerTests().state()
        s.update(model_fingerprint=fingerprint(), pending=None, audits={})
        now=datetime.fromisoformat('2026-11-03T08:17:00+00:00')
        s=observe(s,fixtures.Data(['2026-10-30','2026-11-02'],{}),None,now)
        s['valuation_fx']['2026-11-02']=dict(date='2026-11-02',usdsek=9.8)
        report=export(dict(initial_sek=20000,status='PAPER_READY_AWAITING_SESSION'),s,now)
        result=check(s,report)
        self.assertEqual(result['sessions'],1)
        self.assertEqual(result['trades'],0)
        self.assertEqual(result['nav_sek'],19600)
        with self.assertRaises(AssertionError):
            check(s,dict(report,nav_sek=20000))


class AvanzaSnapshot(unittest.TestCase):
    def test_monthly_rank_uses_uncapped_universe_and_verified_daily_marks(self):
        from unittest.mock import patch
        from avanza10_snapshot import build_snapshot
        def candidate(ticker, cik, growth, price):
            return dict(ticker=ticker,cik=cik,name=ticker,sic='3571',division='Manufacturing',
                        price_usd=price,price_as_of='2026-11-02',relative_strength=.2,data_status='VERIFIED',resolved=True,
                        fundamental_audit={'status':'PASS'},
                        fundamental=dict(qualified=True,metrics=dict(revenue_growth=growth,eps_growth=growth,margin_change=growth)))
        aaa=candidate('AAA','0000000001',1,20)
        bbb=candidate('BBB','0000000002',2,900)
        records=[dict(r,type='CS',primary_exchange='XNAS',active=True) for r in (aaa,bbb)]
        prices={'AAA':[20,20,10000],'BBB':[900,900,10000]}
        data=SimpleNamespace(sessions=['2026-11-02'],universe=lambda day:records,bars=lambda day:prices,splits_by_ticker={})
        report=dict(generated_at='2026-11-03T09:00:00+00:00',price_as_of='2026-11-02',risk_on=True,
                    fx={'usdsek':10},candidates=[aaa])
        def closes(data,day,ticker,count):
            return [100]+[100]*(count-1) if ticker=='SPY' else [120]+[100]*(count-1)
        with patch('avanza10_snapshot.market_universe',return_value=([aaa,bbb],{},True)) as universe, \
             patch('avanza10_snapshot.fundamentals',return_value=bbb) as fundamental, \
             patch('avanza10_snapshot.closes_at',side_effect=closes):
            first=build_snapshot(report,{},data,None)
            universe.assert_called_with(data,'2026-11-02',float('inf'))
            fundamental.assert_called_once_with(bbb,None)
            self.assertEqual([r['ticker'] for r in first['selection']['rows']],['BBB','AAA'])
            self.assertEqual(first['reused_fundamentals'],1)
            prices['BBB']=[900,950,10000]
            later=build_snapshot(report,first,data,None)
            self.assertEqual(later['selection'],first['selection'])
            self.assertEqual(later['quotes']['BBB'],950)
            fundamental.return_value=dict(bbb,data_status='DATA_GAP',resolved=False)
            blocked=build_snapshot(report,first,data,None)
            self.assertFalse(blocked['selection_verified'])
            self.assertEqual(blocked['selection'],first['selection'])
            self.assertIsNone(build_snapshot(report,{},data,None)['selection'])
            # An incomplete month can recover when ten industry-compatible names appear.
            extra=[dict(candidate(f'T{i}',str(i).zfill(10),i,30),sic=sic,division=sector)
                   for i,(sic,sector) in enumerate([('2010','Manufacturing'),('2100','Manufacturing'),
                       ('4010','Transport/communications'),('4100','Transport/communications'),
                       ('4200','Transport/communications'),('4300','Transport/communications'),
                       ('5010','Wholesale'),('5100','Wholesale')],start=3)]
            all_rows=[aaa,bbb,*extra]
            universe.return_value=(all_rows,{},True)
            data.universe=lambda day:[dict(r,type='CS',primary_exchange='XNAS',active=True) for r in all_rows]
            prices.update({r['ticker']:[30,30,10000] for r in extra})
            complete=build_snapshot(dict(report,candidates=all_rows),first,data,None)
            self.assertEqual(complete['selection']['target_count'],10)
            self.assertEqual(complete['selection']['month'],first['selection']['month'])


if __name__=='__main__':unittest.main()
