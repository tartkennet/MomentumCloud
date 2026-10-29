import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path

from h3_observability import build,prefix,metrics,audit_delta,next_attempt,verify_policy

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'h3_forward_policy.json').read_text())


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix=='.gz':
        with gzip.open(path,'wt') as f:json.dump(value,f)
    else:path.write_text(json.dumps(value))


def account(day='2026-10-29'):
    return {'cash':100000.,'shares':{},'receivables':[],'fees':0.,'trades':[],'targets':[],
            'pending':{'signal_date':day,'signal_nav':100000.,'targets':[{'ticker':'SPY','weight':.01}]},
            'last_date':day,'first_is_month_boundary':False,
            'equity':[{'date':day,'nav':100000.,'cash':100000.,'stock_value':0.,'receivables':0.,'fees_cumulative':0.}]}


def checkpoint():
    return dict(source_fingerprint=POLICY['source_fingerprint'],**{k:account() for k in ('strategy','benchmark','stress_strategy','stress_benchmark')})


class ObservabilityTests(unittest.TestCase):
    def test_financial_or_execution_requirements_cannot_be_relaxed(self):
        verify_policy(POLICY)
        changed=copy.deepcopy(POLICY);changed['minimum_daily_drawdown_pct']=-21
        with self.assertRaises(ValueError):verify_policy(changed)
        changed=copy.deepcopy(POLICY);changed['automatic_live_go_allowed']=True
        with self.assertRaises(ValueError):verify_policy(changed)
    def test_waiting_never_displays_backtest_as_forward_nav_or_a_fake_curve(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);record=root/'record'
            write(record/'Momentum_core_paper_identity.json',{'source_fingerprint':POLICY['source_fingerprint'],'cohort':POLICY['cohort']})
            write(record/'Momentum_core_decision.json',{'model':POLICY['model'],'status':'PAPER_WAITING_FOR_SESSIONS','live_approved':False,'broker_orders_enabled':False})
            result=build(record,root/'old',root/'cache',ROOT,POLICY,now=datetime(2026,10,29,14,tzinfo=timezone.utc),verify_git=False)
        self.assertEqual(result['status'],'PAPER_WAITING_FOR_SESSIONS')
        self.assertIsNone(result['metrics']);self.assertEqual(result['holdings'],[]);self.assertEqual(result['curve'],[])
        self.assertEqual(result['validation']['remaining_periods'],30)
        self.assertEqual(result['historical']['metrics']['TotalReturn_pct'],77.13466627290009)

    def test_old_equity_or_current_state_cannot_be_rewritten_in_noop_run(self):
        before=checkpoint();after=copy.deepcopy(before)
        after['strategy']['equity'][0]['nav']=99999
        with self.assertRaises(ValueError):prefix(before,after,POLICY)
        after=copy.deepcopy(before);after['stress_benchmark']['cash']+=1
        with self.assertRaises(ValueError):prefix(before,after,POLICY)

    def test_bootstrap_after_deadline_is_blocked_without_zero_return_pass(self):
        with tempfile.TemporaryDirectory() as name:
            r=Path(name)
            write(r/'Momentum_core_paper_identity.json',{'source_fingerprint':POLICY['source_fingerprint'],'cohort':POLICY['cohort']})
            write(r/'Momentum_core_decision.json',{'model':POLICY['model'],'status':'PAPER_WAITING_FOR_SESSIONS'})
            result=build(r,r/'old',r/'cache',ROOT,POLICY,now=datetime(2026,10,30,13,tzinfo=timezone.utc),verify_git=False)
        self.assertEqual(result['validation']['status'],'DATA_BLOCKED');self.assertIsNone(result['metrics'])
        self.assertFalse(result['live_approved'])

    def test_one_day_raw_fill_fee_cash_shares_and_nav_reconciled_independently(self):
        old=checkpoint();new=copy.deepcopy(old);day='2026-10-30'
        for name in ('strategy','benchmark','stress_strategy','stress_benchmark'):
            a=new[name];fee=3. if name.startswith('stress_') else 1.5
            a.update(cash=99000-fee,shares={'SPY':10},fees=fee,last_date=day,pending=None)
            a['trades'].append({'date':day,'signal_date':'2026-10-29','side':'BUY','ticker':'SPY','quantity':10,'price':100.,'fee':fee})
            a['equity'].append({'date':day,'nav':100010-fee,'cash':99000-fee,'stock_value':1010.,'receivables':0.,'fees_cumulative':fee})
        observed={'splits/2025-04-01/2026-10-30':[], 'dividends/2026-10-30/2026-10-30':[],
                  'calendar/2025-04-01/2026-10-30':{'sessions':['2026-10-29',day]},'raw/'+day:{'SPY':[100.,101.,1000000]}}
        inputs={k:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest() for k,v in observed.items()}
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            write(root/'raw-v1'/f'{day}.json.gz',{'basis':'RAW','date':day,'bars':{'SPY':[100.,101.,1000000]}})
            write(root/'splits-2025-04-01-2026-10-30-v1.json.gz',[])
            write(root/'dividends-2026-10-30-2026-10-30-v1.json.gz',[])
            write(root/'calendar-v1/2025-04-01_2026-10-30.json.gz',{'sessions':['2026-10-29',day]})
            result=audit_delta(old,new,root,inputs,{'cash':{},'stock':{},'distributions':[]})
            self.assertEqual(result['status'],'PASS');self.assertEqual(result['market_trade_rows_checked'],4)
            new['strategy']['trades'][-1]['price']=99
            with self.assertRaises(ValueError):audit_delta(old,new,root,inputs,{'cash':{},'stock':{},'distributions':[]})
            new['strategy']['trades'][-1]['price']=100
            new['strategy']['trades'][-1]['quantity']=9
            with self.assertRaises(ValueError):audit_delta(old,new,root,inputs,{'cash':{},'stock':{},'distributions':[]})
            new['strategy']['trades'][-1]['quantity']=10
            inputs['raw/'+day]='0'*64
            with self.assertRaises(ValueError):audit_delta(old,new,root,inputs,{'cash':{},'stock':{},'distributions':[]})

    def test_first_thirty_complete_intervals_are_fixed_despite_later_winner(self):
        a=account();b=account()
        for i in range(32):
            year=2026+(10+i)//12;month=(10+i)%12+1;day=f'{year:04}-{month:02}-01'
            a['equity'].append({'date':day,'nav':100000*1.01**(i+1),'fees_cumulative':i})
            b['equity'].append({'date':day,'nav':100000*1.005**(i+1),'fees_cumulative':i})
        before=metrics(a,b);a['equity'][-1]['nav']*=100
        self.assertEqual(before,metrics(a,b))
        self.assertEqual(before['Periods'],30);self.assertTrue(before['fixed_first_window_complete'])
        self.assertTrue(before['evaluation_through'].startswith('2029-05'))

    def test_schedule_skips_days_without_a_morning_run(self):
        # Saturday's final retry is followed by Tuesday's first scheduled attempt.
        now=datetime(2026,10,31,9,36,tzinfo=timezone.utc)
        self.assertEqual(next_attempt(now),'2026-11-03T00:35:00+00:00')
