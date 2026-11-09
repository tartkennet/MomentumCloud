import copy,json,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_best_v2 import formation
from quality_sources import DataUnavailable
from quality_forward import digest
import best_v2_forward as controller
import best_v2_execution as execution
import audit_best_v2 as audit
from avanza10_forward import summarize


def fixture():
    data,r,_=formation();commit=datetime.fromisoformat('2026-11-09T22:00:00+00:00')
    initial=datetime.fromisoformat('2026-11-07T09:28:00+00:00')
    state=controller.initialize(r,initial);controller.decide(state,r,data,initial)
    old=copy.deepcopy(state['pending'])
    execution.register(state,SimpleNamespace(sessions=['2026-11-06','2026-11-09']),commit)
    controller.decide(state,r,data,commit+timedelta(seconds=1))
    now=datetime.fromisoformat('2026-11-10T15:16:00+00:00');start=datetime.fromisoformat('2026-11-10T15:00:00+00:00')
    prices={x['ticker']:x['price_usd'] for x in state['pending']['targets']};prices['SPY']=state['pending']['benchmark_order']['limit']/1.02
    class Client:
        calls=[]
        overrides={}
        def get(self,path,params):
            self.calls.append(path);t=path.split('/')[4]
            if t in self.overrides:
                x=self.overrides[t]
                if isinstance(x,Exception):raise x
                return dict(x,ticker=x.get('ticker',t),adjusted=x.get('adjusted',False))
            p=prices[t]
            return dict(status='DELAYED',ticker=t,adjusted=False,results=[dict(t=int(start.timestamp()*1000),o=p,c=p,h=p*1.001,l=p*.999,v=500)])
    return state,r,now,Client(),old

class ExecutionTests(unittest.TestCase):
    def observe(self,s,client,now,sessions=None):
        with patch('avanza10_forward.observe_account',side_effect=lambda state,*args:state),patch('best_v2_execution.events'):
            return execution.observe(s,SimpleNamespace(sessions=sessions or ['2026-11-06','2026-11-09']),client,now,clock=lambda:now)

    def test_migration_preserves_old_decision_capital_and_records_missed_monday(self):
        s,r,now,c,old=fixture()
        self.assertEqual(s['decisions'][0],old);self.assertEqual(s['initial_sek'],25000)
        self.assertEqual(s['execution_attempts'][0]['status'],'MISSED_OPEN_NO_BACKFILL')
        self.assertEqual(len(s['execution_attempts'][0]['orders']),10)
        self.assertEqual(s['gaps'][0]['session'],'2026-11-09')
        self.assertEqual(s['cancelled_intentions'][0]['commitment'],old['sha256'])
        self.assertEqual([x['ticker'] for x in s['pending']['targets']],[x['ticker'] for x in old['targets']])

    def test_new_session_prices_keep_committed_quantities_limits_and_hash(self):
        s,r,now,c,_=fixture();before=copy.deepcopy(s['pending'])
        r['price_as_of']='2026-11-09'
        r['signal']['quotes']={t:p*1.25 for t,p in r['signal']['quotes'].items()}
        controller.decide(s,r,None,now)
        self.assertEqual(s['pending'],before)
        self.assertEqual(s['initial_sek'],25000)

    def test_realistically_delayed_completed_minutes_book_at_observation_and_audit(self):
        s,r,now,c,_=fixture();s=self.observe(s,c,now)
        self.assertEqual(len(s['strategy']['trades']),10);self.assertEqual(len(s['strategy']['shares']),10)
        self.assertEqual(s['execution_outcome']['filled'],10)
        for key in ('strategy','benchmark'):
            for t in s[key]['trades']:
                self.assertEqual(t['execution_at'],now.isoformat());self.assertNotEqual(t['execution_at'],t['price_as_of'])
        for t in s['strategy']['trades']:s['trade_fx'][t['date']]={'date':t['date'],'usdsek':10}
        s['audits']={k:audit.audit_account(s,k,k=='benchmark') for k in ('strategy','benchmark')}
        p=summarize(s,r['signal'],now);audit.account(s,p)
        before=copy.deepcopy(s['strategy']);s=self.observe(s,c,now+timedelta(minutes=1));self.assertEqual(s['strategy'],before)
        bad=copy.deepcopy(s);bad['opening_quotes'][0]['intraday_receipts'][bad['strategy']['trades'][0]['ticker']]['raw']['t']-=86400000
        with self.assertRaises(AssertionError):audit.audit_execution(bad)

    def test_provider_empty_or_missing_entitlement_has_ten_reasons_no_fills(self):
        for failure in ({'status':'DELAYED','results':[]},DataUnavailable('HTTP_403')):
            s,r,now,c,_=fixture();c.overrides={t:failure for t in [x['ticker'] for x in s['pending']['targets']]+['SPY']}
            s=self.observe(s,c,now)
            self.assertFalse(s['strategy']['trades']);self.assertEqual(len(s['execution_outcome']['orders']),10)
            self.assertTrue(all(x['reason'] in ('OPEN_PRICE_UNAVAILABLE','OPEN_PRICE_NO_ENTITLEMENT') for x in s['execution_outcome']['orders']))

    def test_partial_quote_batch_and_price_gap_do_not_create_partial_initial_portfolio(self):
        for problem in ('empty','limit'):
            s,r,now,c,_=fixture();t=s['pending']['targets'][0]['ticker'];price=s['pending']['plan']['orders'][0]['limit']*10
            c.overrides={t:{'status':'OK','ticker':t,'adjusted':False,'results':[] if problem=='empty' else [dict(t=1794322800000,o=price,c=price,h=price,l=price,v=500)]}}
            s=self.observe(s,c,now);self.assertFalse(s['strategy']['trades']);self.assertEqual(len(s['execution_outcome']['orders']),10)
            self.assertTrue(all(x['reason'] for x in s['execution_outcome']['orders']))

    def test_future_old_premarket_unfinished_adjusted_and_wrong_day_are_rejected(self):
        s,r,now,c,_=fixture();p=s['pending'];registered=execution.aware(s['execution_policy']['registered_at']);committed=execution.aware(p['created_at'])
        raw=dict(t=int(datetime.fromisoformat('2026-11-10T15:00:00Z').timestamp()*1000),o=10,c=10,h=10,l=10,v=100)
        cases=[('2026-11-09T15:00:00Z','WRONG_QUOTE_SESSION'),('2026-11-10T14:29:00Z','OUTSIDE_REGULAR_EXECUTION_MINUTE'),('2026-11-10T15:16:00Z','UNFINISHED_OR_FUTURE_MINUTE'),('2026-11-10T14:50:00Z','OPEN_PRICE_PROVIDER_DELAY')]
        for timestamp,code in cases:
            changed=dict(raw,t=int(datetime.fromisoformat(timestamp).timestamp()*1000))
            with self.assertRaisesRegex(DataUnavailable,code):execution.validate_bar(changed,now,committed,registered)
        with self.assertRaisesRegex(DataUnavailable,'QUOTE_PRECEDES_COMMITMENT'):execution.validate_bar(raw,now,now,registered)

    def test_sunday_monday_rollover_and_postwindow_never_query_or_backfill(self):
        for stamp in ('2026-11-08T15:16:00Z','2026-11-09T15:16:00Z','2026-11-10T21:16:00Z'):
            s,r,now,c,_=fixture();c.calls=[];s=self.observe(s,c,datetime.fromisoformat(stamp),['2026-11-06','2026-11-09','2026-11-10'])
            self.assertFalse(s['strategy']['trades']);self.assertFalse(c.calls)
        self.assertEqual(s['execution_outcome']['status'],'MISSED_OPEN_NO_BACKFILL')
        count=len(s['gaps']);self.observe(s,c,datetime.fromisoformat('2026-11-10T22:16:00Z'),['2026-11-06','2026-11-09','2026-11-10']);self.assertEqual(len(s['gaps']),count)

    def test_old_1532_schedule_cannot_explain_an_absent_run(self):
        # Calendar availability, freshness and execution eligibility are separate.
        from best_data import completed_end
        now=datetime.fromisoformat('2026-11-09T18:56:14Z')
        self.assertEqual(completed_end(now),'2026-11-08')
        self.assertEqual(now.astimezone(execution.NY).hour,13)

    def test_identity_adjustment_delay_and_invalid_volume_have_explicit_failures(self):
        s,r,now,c,_=fixture();t=s['pending']['targets'][0]['ticker'];p=s['pending'];registered=execution.aware(s['execution_policy']['registered_at']);committed=execution.aware(p['created_at'])
        for body,code in [({'status':'OK','ticker':'WRONG','adjusted':False,'results':[]},'INVALID_INTRADAY_IDENTITY'),({'status':'OK','ticker':t,'adjusted':True,'results':[]},'ADJUSTED_MINUTE_NOT_ALLOWED')]:
            c.overrides={t:body}
            with self.assertRaisesRegex(DataUnavailable,code):execution.quote(c,t,now,committed,registered)
        raw=dict(t=int(datetime.fromisoformat('2027-06-15T14:00:00Z').timestamp()*1000),o=10,c=10,h=11,l=9,v=100)
        summer=datetime.fromisoformat('2027-06-15T14:16:00Z')
        execution.validate_bar(raw,summer,committed,registered)
        with self.assertRaisesRegex(DataUnavailable,'INVALID_MINUTE_OHLCV'):execution.validate_bar(dict(raw,v=0),summer,committed,registered)

    def test_network_time_crossing_deadline_cannot_book_late(self):
        s,r,now,c,_=fixture()
        with patch('avanza10_forward.observe_account',side_effect=lambda state,*args:state),patch('best_v2_execution.events'):
            result=execution.observe(s,SimpleNamespace(sessions=['2026-11-09']),c,now,clock=lambda:datetime.fromisoformat('2026-11-10T21:00:00Z'))
        self.assertFalse(result['strategy']['trades']);self.assertEqual(result['execution_outcome']['status'],'MISSED_OPEN_NO_BACKFILL')

    def test_retained_ten_complete_monthly_check_without_invented_trades(self):
        s,r,now,c,_=fixture();s=self.observe(s,c,now);n=len(s['strategy']['trades'])
        p=copy.deepcopy(s['decisions'][-1]);p.pop('sha256');p['created_at']='2026-11-30T22:00:00+00:00';p['signal_date']='2026-11-30';p['plan']['orders']=[];p['sha256']=digest(p)
        s['pending']=p;s['decisions'].append(copy.deepcopy(p));c.calls=[]
        s=self.observe(s,c,datetime.fromisoformat('2026-12-01T15:16:00Z'))
        self.assertEqual(len(s['strategy']['trades']),n);self.assertFalse(c.calls)
        self.assertEqual(s['execution_outcome']['status'],'RETAINED_NO_TRADES');self.assertEqual(s['decision_month'],'2026-12')

    def test_locked_month_requires_all_ten_members_not_an_unheld_research_candidate(self):
        data,r,now=formation();rows=copy.deepcopy(r['ranked_liquid']);calls=[]
        def verify(row,*args):calls.append(row['ticker']);return dict(row,event_status='CLEAR',reference_sha256='proof')
        with patch('best_v2_forward.reference',side_effect=verify):
            result=controller.locked_member_references(rows,r['signal']['selection'],'2026-11-05',Path('.'))
        self.assertEqual(set(calls),{x['ticker'] for x in r['targets']});self.assertEqual(len(result),10)
        missing=[x for x in rows if x['ticker']!=r['targets'][0]['ticker']]
        with patch('best_v2_forward.reference',side_effect=verify):
            with self.assertRaisesRegex(ValueError,'COMMITTED_MEMBER_PRICE'):controller.locked_member_references(missing,r['signal']['selection'],'2026-11-05',Path('.'))
        with patch('best_v2_forward.reference',side_effect=lambda row,*a:dict(row,event_status='DATA_BLOCKED')):
            with self.assertRaisesRegex(ValueError,'COMMITTED_MEMBER_CORPORATE_EVENT'):controller.locked_member_references(rows,r['signal']['selection'],'2026-11-05',Path('.'))
