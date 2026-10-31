import copy,unittest
from datetime import datetime
from types import SimpleNamespace
import test_quality_earnings as fixture_tests
from quality_forward import digest
from quality_account_audit import audit_account
from run_quality_forward import observe,export


class Data:
    def __init__(self,days,bars,dividends=None,splits=None):
        self.sessions=days;self._bars=bars;self.splits=[];self.dividends=[];self.cash_actions={};self.stock_actions={};self.distributions=[];self._splits=splits or [];self._dividends=dividends or []
    def set_day(self,day):
        self.splits=[r for r in self._splits if r['execution_date']==day];self.dividends=[r for r in self._dividends if r['ex_dividend_date']==day]
    def bars(self,day):return self._bars
    def native_usd(self,day,currency):return 1 if currency=='USD' else .75


class ControllerTests(unittest.TestCase):
    def state(self):
        s=fixture_tests.ForwardTimingTests().pending();s.update(opening_quotes=[],valuation_fx={})
        return s
    def test_future_open_to_next_observed_close_and_independent_audit(self):
        s=self.state();bars={o['ticker']:[19,20,100000] for o in s['pending']['plan']['orders']};bars['SPY']=[300,303,1000000]
        client=SimpleNamespace(get=lambda *args,**kwargs:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in bars.items()]})
        s=observe(s,Data(['2026-10-30'],bars),client,datetime.fromisoformat('2026-11-02T15:15:00+00:00'))
        self.assertEqual(len(s['strategy']['shares']),10);self.assertFalse(s['strategy']['equity'])
        self.assertEqual(audit_account(s,'strategy')['trades'],10)
        s=observe(s,Data(['2026-10-30','2026-11-02'],bars),client,datetime.fromisoformat('2026-11-03T08:15:00+00:00'))
        self.assertEqual(len(s['strategy']['equity']),1);self.assertEqual(audit_account(s,'strategy')['valuations'],1)
        bad=copy.deepcopy(s);bad['strategy']['trades'][0]['quantity']+=1
        with self.assertRaises(AssertionError):audit_account(bad,'strategy')
    def test_split_dividend_then_payment_independently_reconcile(self):
        s=self.state();bars={o['ticker']:[19,20,100000] for o in s['pending']['plan']['orders']};bars['SPY']=[300,303,1000000]
        client=SimpleNamespace(get=lambda *args,**kwargs:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in bars.items()]})
        s=observe(s,Data(['2026-10-30'],bars),client,datetime.fromisoformat('2026-11-02T15:15:00+00:00'))
        ticker=next(iter(s['strategy']['shares']));q=s['strategy']['shares'][ticker]
        split=dict(ticker=ticker,execution_date='2026-11-03',split_from=1,split_to=2)
        dividend=dict(ticker=ticker,ex_dividend_date='2026-11-03',cash_amount=.5,currency='CAD',pay_date='2026-11-04')
        d=Data(['2026-10-30','2026-11-02','2026-11-03'],bars,[dividend],[split])
        s=observe(s,d,client,datetime.fromisoformat('2026-11-04T08:15:00+00:00'))
        self.assertEqual(s['strategy']['shares'][ticker],q*2);self.assertEqual(audit_account(s,'strategy')['status'],'PASS')
        d=Data(['2026-10-30','2026-11-02','2026-11-03','2026-11-04'],bars,[dividend],[split])
        s=observe(s,d,client,datetime.fromisoformat('2026-11-05T08:15:00+00:00'))
        self.assertTrue(s['strategy']['fx_payments']);self.assertEqual(audit_account(s,'strategy')['status'],'PASS')
    def test_same_day_after_open_decision_cannot_use_that_open(self):
        from quality_forward import process
        s=self.state();p=s['pending'];p['created_at']='2026-11-02T15:00:00+00:00';p.pop('sha256');p['sha256']=digest(p);s['decisions']=[copy.deepcopy(p)]
        got=process(s,{},datetime.fromisoformat('2026-11-02T15:15:00+00:00'),['2026-11-02'],{'T1':[19,20,1000]})
        self.assertFalse(got['strategy']['trades']);self.assertIsNotNone(got['pending'])

    def test_new_risk_off_cancels_pending_buys_without_rewriting_decision(self):
        from run_quality_forward import decide
        s=self.state();prior=copy.deepcopy(s['decisions']);decide(s,dict(risk_on=False,price_as_of='2026-10-30'),None,datetime.fromisoformat('2026-10-31T16:00:00+00:00'))
        self.assertIsNone(s['pending']);self.assertEqual(s['decisions'],prior);self.assertEqual(s['cancelled_intentions'][0]['reason'],'RISK_OFF');self.assertFalse(s['strategy']['trades'])

    def test_financial_statistics_include_costs_and_benchmark_fx(self):
        from run_quality_forward import export
        from quality_account_audit import audit_statistics
        s=self.state();p=s['pending'];p['benchmark_order']=dict(quantity=6,limit=306);p.pop('sha256');p['sha256']=digest(p);s['decisions']=[copy.deepcopy(p)]
        bars={o['ticker']:[19,20,100000] for o in p['plan']['orders']};bars['SPY']=[300,303,1000000]
        client=SimpleNamespace(get=lambda *args,**kwargs:{'results':[dict(T=t,o=b[0],c=b[1],v=b[2]) for t,b in bars.items()]})
        s=observe(s,Data(['2026-10-30'],bars),client,datetime.fromisoformat('2026-11-02T15:15:00+00:00'))
        self.assertEqual(audit_account(s,'benchmark',True)['status'],'PASS')
        s=observe(s,Data(['2026-10-30','2026-11-02'],bars),client,datetime.fromisoformat('2026-11-03T08:15:00+00:00'))
        s['valuation_fx']['2026-11-02']=dict(usdsek=10,date='2026-11-02');s['audits']={}
        report=export({},s,datetime.fromisoformat('2026-11-03T08:15:00+00:00'))
        self.assertEqual(report['independent_statistics']['status'],'PASS');self.assertIsNone(report['sharpe'])
        self.assertAlmostEqual(report['paper_metrics']['TotalReturn_pct'],100*(s['strategy']['equity'][-1]['nav']/2000-1))
        report['paper_metrics']['DailyMaxDrawdown_pct']=-50
        with self.assertRaises(AssertionError):audit_statistics(s,report)

    def test_nonfinite_or_zero_volume_quotes_never_create_trades(self):
        from quality_forward import process
        s=self.state();orders=s['pending']['plan']['orders'];bars={o['ticker']:[float('nan'),20,0] for o in orders}
        got=process(s,{},datetime.fromisoformat('2026-11-02T15:15:00+00:00'),['2026-11-02'],bars)
        self.assertFalse(got['strategy']['trades']);self.assertEqual(len(got['unfilled_orders']),10)


if __name__=='__main__':unittest.main()
