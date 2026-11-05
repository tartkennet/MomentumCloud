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
    def test_monthly_rank_is_locked_and_daily_quotes_remain_current(self):
        from avanza10_snapshot import build_snapshot
        def candidate(ticker, growth):
            return dict(ticker=ticker,cik=ticker,name=ticker,sic='3571',division='Manufacturing',
                        price_usd=20,price_as_of='2026-11-02',data_status='VERIFIED',
                        fundamental=dict(qualified=True,metrics=dict(revenue_growth=growth,eps_growth=growth,margin_change=growth)))
        rows=[candidate('AAA',1),candidate('BBB',2)]
        report=dict(generated_at='2026-11-03T09:00:00+00:00',price_as_of='2026-11-02',coverage=.90,risk_on=True,
                    status='PAPER_READY_AWAITING_SESSION',collection_status='PAPER_READY_AWAITING_SESSION',
                    audits={'selection':{'status':'PASS'}},fx={'usdsek':10},candidates=rows)
        first=build_snapshot(report)
        self.assertEqual([r['ticker'] for r in first['selection']['rows']],['BBB','AAA'])
        later=build_snapshot(dict(report,candidates=[dict(rows[0],price_usd=30)]),first)
        self.assertEqual(later['selection'],first['selection'])
        self.assertEqual(later['quotes'],{'AAA':30})
        blocked=build_snapshot(dict(report,status='COLLECTION_FAILED'),first)
        self.assertFalse(blocked['market_verified'])
        self.assertFalse(blocked['quotes'])
        self.assertEqual(blocked['selection'],first['selection'])
        insufficient=build_snapshot(dict(report,coverage=.89))
        self.assertIsNone(insufficient['selection'])
        self.assertFalse(insufficient['selection_verified'])
        new_month=build_snapshot(dict(report,generated_at='2026-12-01T09:00:00+00:00',price_as_of='2026-11-30'),first)
        self.assertEqual(new_month['selection']['month'],'2026-12')


if __name__=='__main__':unittest.main()
