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


if __name__=='__main__':unittest.main()
