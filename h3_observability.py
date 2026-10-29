"""Independent observation/validation around the UNCHANGED frozen H3 engine.

Reads accepted checkpoints, cached raw inputs and literal verified event facts.
No strategy/ledger/metric imports, network calls, order submission or backfill.
"""
import argparse
import ast
import copy
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tarfile
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ACCOUNTS=('strategy','benchmark','stress_strategy','stress_benchmark')


def verify_policy(policy):
    fixed={'minimum_periods':30,'minimum_daily_drawdown_pct':-20,'minimum_hit_rate_pct':50,
           'costs_one_way_bps':[15,30],'positive_net_return_strict':True,'positive_edge_vs_spy_strict':True,
           'require_both_cost_cases':True,'cash_interest':0,'sharpe_risk_free_rate':0,
           'sharpe_annualization_sessions':252,'execution_review_required':True,
           'automatic_live_go_allowed':False,'explicit_user_approval_required_for_live':True,
           'live_approved':False,'broker_orders_enabled':False}
    if any(policy.get(k)!=v for k,v in fixed.items()):raise ValueError('Registered financial/execution policy changed')


def read(path,default=None):
    path=Path(path)
    if not path.exists():return copy.deepcopy(default)
    if path.suffix=='.gz':
        with gzip.open(path,'rt') as f:return json.load(f)
    return json.loads(path.read_text())


def near(a,b,label):
    if not math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-6):raise ValueError('Reconciliation failed: '+label)


def next_attempt(now):
    for n in range(9):
        day=(now+timedelta(days=n)).date()
        if day.weekday() not in (1,2,3,4,5):continue
        for hour in (0,3,6,9):
            value=datetime(day.year,day.month,day.day,hour,35,tzinfo=timezone.utc)
            if value>now:return value.isoformat()
    raise ValueError('No next scheduled attempt')


def verify_source(engine,policy):
    """Compare every archived file with its trusted Git blob at the fixed commit."""
    sha=policy['frozen_source_commit'];engine=Path(engine)
    output=subprocess.check_output(['git','ls-tree','-rz',sha],cwd=ROOT)
    checked=0
    for entry in output.split(b'\0'):
        if not entry:continue
        meta,name=entry.split(b'\t',1);mode,kind,oid=meta.split()
        if kind!=b'blob':raise ValueError('Unsupported frozen source entry')
        path=engine/name.decode()
        if mode not in (b'100644',b'100755') or path.is_symlink():raise ValueError('Unsupported frozen source file')
        body=path.read_bytes();actual=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
        if actual!=oid.decode():raise ValueError('Frozen file differs from committed source: '+name.decode())
        checked+=1
    return {'status':'PASS','git_commit':sha,'files_checked':checked}


def metrics(strategy,benchmark,limit=30):
    rows=strategy['equity'];other=benchmark['equity']
    if not rows:return None
    if [r['date'] for r in rows]!=[r['date'] for r in other]:raise ValueError('Unaligned accepted dates')
    boundaries=[i for i in range(1,len(rows)) if rows[i]['date'][:7]!=rows[i-1]['date'][:7]]
    if strategy.get('first_is_month_boundary'):boundaries.insert(0,0)
    end=boundaries[limit] if len(boundaries)>limit else len(rows)-1
    boundaries=[i for i in boundaries if i<=end]
    returns=[100*(rows[b]['nav']/rows[a]['nav']-1) for a,b in zip(boundaries,boundaries[1:])]
    nav=[r['nav'] for r in rows[:end+1]];spy=[r['nav'] for r in other[:end+1]]
    daily=[b/a-1 for a,b in zip(nav,nav[1:])]
    mean=math.fsum(daily)/len(daily) if daily else 0.
    variance=math.fsum((r-mean)**2 for r in daily)/(len(daily)-1) if len(daily)>1 else 0.
    peak=nav[0];dd=0.
    for value in nav:peak=max(peak,value);dd=min(dd,100*(value/peak-1))
    total=100*(nav[-1]/nav[0]-1);spy_total=100*(spy[-1]/spy[0]-1)
    return {'Periods':len(returns),'TotalReturn_pct':total,'SPYTotalReturn_pct':spy_total,
            'TotalEdgeVsSPY_pct':total-spy_total,'DailyMaxDrawdown_pct':dd,
            'PeriodHitRate_pct':100*sum(r>0 for r in returns)/len(returns) if returns else 0.,
            'DailySharpe_zero_rf':math.sqrt(252)*mean/math.sqrt(variance) if variance else None,
            'ActualFees_USD':rows[end]['fees_cumulative'],'FinalNAV_USD':nav[-1],
            'evaluation_through':rows[end]['date'],'sessions_in_evaluation':end+1,
            'fixed_first_window_complete':len(returns)>=limit}


def gates(m,p):
    specs=[('at_least_30_periods','Periods',p['minimum_periods'],lambda x,y:x>=y),
           ('positive_net_return','TotalReturn_pct',0,lambda x,y:x>y),
           ('beats_spy','TotalEdgeVsSPY_pct',0,lambda x,y:x>y),
           ('drawdown','DailyMaxDrawdown_pct',p['minimum_daily_drawdown_pct'],lambda x,y:x>=y),
           ('hit_rate','PeriodHitRate_pct',p['minimum_hit_rate_pct'],lambda x,y:x>=y)]
    return [{'gate':name,'value':m.get(key) if m else None,'threshold':threshold,
             'pass':bool(m and test(m[key],threshold))} for name,key,threshold,test in specs]


def prefix(previous,current,policy):
    if current['source_fingerprint']!=policy['source_fingerprint']:raise ValueError('Wrong forward source identity')
    if previous and previous['source_fingerprint']!=current['source_fingerprint']:raise ValueError('Changed checkpoint identity')
    sessions=None
    for name in ACCOUNTS:
        account=current[name];dates=[r['date'] for r in account['equity']]
        if dates!=sorted(set(dates)) or not dates or dates[0]!=policy['start']:raise ValueError('Invalid prospective calendar')
        if account['last_date']!=dates[-1]:raise ValueError('Wrong accepted as-of date')
        if sessions is None:sessions=dates
        if dates!=sessions:raise ValueError('Four accounts have different dates')
        old=previous[name] if previous else None
        if old:
            if account['last_date']<old['last_date']:raise ValueError('Forward record moved backwards')
            for field,date_key in (('equity','date'),('trades','date'),('targets','date')):
                if [r for r in account[field] if r[date_key]<=old['last_date']]!=old[field]:
                    raise ValueError('Previously recorded '+field+' changed')
            if account['last_date']==old['last_date'] and account!=old:raise ValueError('Unchanged session has modified state')
        new=[r for r in account['equity'] if not old or r['date']>old['last_date']]
        if len(new)>1:raise ValueError('Unrecorded sessions cannot be reconstructed')
    return sessions


def facts(engine):
    variables={}
    for name in ('backtest_momentum_v3.py','research_core_actions.py','research_core_ledger.py'):
        for node in ast.parse((Path(engine)/name).read_text()).body:
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Name) and target.id in ('CASH_CORPORATE_ACTIONS','STOCK_CORPORATE_ACTIONS','EXTRA_CASH_ACTIONS','CASH_COMPLETIONS','STOCK_COMPLETIONS','DISTRIBUTIONS'):
                        variables[target.id]=ast.literal_eval(node.value)
    return {'cash':dict(variables['CASH_CORPORATE_ACTIONS'],**variables['EXTRA_CASH_ACTIONS'],**variables['CASH_COMPLETIONS']),
            'stock':dict(variables['STOCK_CORPORATE_ACTIONS'],**variables['STOCK_COMPLETIONS']),
            'distributions':variables['DISTRIBUTIONS']}


def audit_delta(previous,current,cache,inputs,event_facts):
    cache=Path(cache);day=current['strategy']['last_date']
    if previous and previous['strategy']['last_date']==day:return {'status':'UNCHANGED_ACCEPTED_PREFIX','new_sessions':0}
    bars=read(cache/'raw-v1'/f'{day}.json.gz')
    if not bars or bars.get('basis')!='RAW' or bars.get('date')!=day:raise ValueError('Missing new raw marks')
    bars=bars['bars'];events={};calendar=None
    def vintage(label,value):
        actual=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        if inputs.get(label)!=actual:raise ValueError('Observed input hash changed: '+label)
    vintage('raw/'+day,bars)
    for label in inputs:
        parts=label.split('/')
        if len(parts)!=3:continue
        kind,start,end=parts
        if kind in ('splits','dividends'):
            values=read(cache/f'{kind}-{start}-{end}-v1.json.gz')
            if values is None:raise ValueError('Missing observed event input')
            vintage(label,values)
            key='execution_date' if kind=='splits' else 'ex_dividend_date'
            events[kind]=[e for e in values if e[key]==day]
        elif kind=='calendar':
            calendar=read(cache/'calendar-v1'/f'{start}_{end}.json.gz');vintage(label,calendar)
    if any(k not in events for k in ('splits','dividends')):raise ValueError('Unidentified event vintage')
    if previous:
        days=calendar['sessions'] if calendar else []
        prior=previous['strategy']['last_date']
        if prior not in days or days[days.index(prior)+1:days.index(prior)+2]!=[day]:raise ValueError('Fill is not at the next observed session')
    checked=0;participation=[]
    for name in ACCOUNTS:
        new=current[name];old=previous[name] if previous else {'cash':100000.,'shares':{},'receivables':[],'fees':0.,'trades':[],'pending':None}
        if new.get('pending'):
            if new['pending']['signal_date']!=day:raise ValueError('New intention was not recorded for the current close')
            near(new['pending']['signal_nav'],new['equity'][-1]['nav'],'new signal NAV')
            weights=[t['weight'] for t in new['pending']['targets']]
            if any(not math.isfinite(w) or w<0 for w in weights) or sum(weights)>1+1e-9:raise ValueError('Invalid unlevered intention weights')
        if any(t['date']!=day for t in new['targets'][len(old.get('targets',[])):]):raise ValueError('Backdated target decision')
        cash=old['cash'];shares=copy.deepcopy(old['shares']);claims=copy.deepcopy(old['receivables']);fees=old['fees']
        def claim(t,amount,pay,reason,maximum=None):
            nonlocal cash
            if pay and pay<=day:cash+=amount
            else:
                row={'ticker':t,'amount':amount,'pay_date':pay,'reason':reason}
                if maximum is not None:row['maximum_amount']=maximum
                claims.append(row)
        for e in events['splits']:
            if e['ticker'] in shares:shares[e['ticker']]*=e['split_to']/e['split_from']
        before=dict(shares)
        for e in events['dividends']:
            if e['ticker'] in shares:
                if e.get('currency','').upper()!='USD' or not e.get('pay_date'):raise ValueError('Unverified held dividend')
                claim(e['ticker'],shares[e['ticker']]*e['cash_amount'],e['pay_date'],'DIVIDEND')
        cash+=sum(c['amount'] for c in claims if c['pay_date'] and c['pay_date']<=day)
        claims=[c for c in claims if not c['pay_date'] or c['pay_date']>day]
        for t,e in event_facts['cash'].items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);claim(t,q*e['cash_per_share'],e.get('pay_date'),'CASH_MERGER')
                if e.get('contingent_cash_per_share',0)>0:claim(t,0.,None,'CONTINGENT_VALUE_RIGHT_UNPRICED',q*e['contingent_cash_per_share'])
        for t,e in event_facts['stock'].items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);other=e['successor_ticker'];shares[other]=shares.get(other,0)+q*e['shares_per_share']
                if e.get('cash_per_share'):claim(t,q*e['cash_per_share'],e.get('pay_date'),'STOCK_MERGER_CASH')
        for e in event_facts['distributions']:
            if e['ex_date']==day:
                q=before.get(e['parent'],0)*e['ratio']
                if q:shares[e['recipient']]=shares.get(e['recipient'],0)+q
        cost=.003 if name.startswith('stress_') else .0015
        # Derive expected whole-share fills solely from the previously sealed
        # intention and today's raw open, independently of the engine's trades.
        planned=[];desired={};pending=old.get('pending')
        if pending:
            for target in pending['targets']:
                t=target['ticker'];cash_event=event_facts['cash'].get(t);stock_event=event_facts['stock'].get(t)
                if cash_event and pending['signal_date']<=cash_event['effective_date']<=day:continue
                if stock_event and pending['signal_date']<=stock_event['effective_date']<=day:t=stock_event['successor_ticker']
                opening=bars.get(t,[None])[0]
                if opening is None:
                    if t in shares:raise ValueError('Missing held opening quote')
                    planned.append(('BUY_CANCELLED_NO_OPEN',t,0));continue
                desired[t]=desired.get(t,0)+math.floor(pending['signal_nav']*target['weight']/opening)
            post_sale=dict(shares);available=cash
            for t,q in sorted(shares.items()):
                sell=math.floor(max(0,q-desired.get(t,0))+1e-9)
                if sell:
                    planned.append(('SELL',t,sell));post_sale[t]-=sell
                    available+=sell*bars[t][0]*(1-cost)
            wanted={t:max(0,math.floor(q-post_sale.get(t,0)+1e-9)) for t,q in desired.items()}
            required=sum(q*bars[t][0]*(1+cost) for t,q in wanted.items() if q)
            scale=min(1.,max(0.,available)/required) if required else 0.
            planned += [('BUY',t,math.floor(q*scale+1e-10)) for t,q in sorted(wanted.items()) if math.floor(q*scale+1e-10)]
        new_trades=new['trades'][len(old['trades']):]
        actual=[(t['side'],t['ticker'],t['quantity']) for t in new_trades if t['side'] in ('BUY','SELL','BUY_CANCELLED_NO_OPEN')]
        if actual!=planned:raise ValueError('Fills differ from the previously recorded intention and available cash')
        for trade in new_trades:
            if trade['date']!=day:raise ValueError('Trade backdated')
            side=trade['side'];t=trade['ticker'];q=trade['quantity']
            if side not in ('BUY','SELL','BUY_CANCELLED_NO_OPEN'):continue
            if not old.get('pending') or trade['signal_date']!=old['pending']['signal_date']:raise ValueError('No previously recorded intention for fill')
            if trade['signal_date']>=day:raise ValueError('Same-session signal fill')
            opening=bars.get(t,[None])[0]
            if side=='BUY_CANCELLED_NO_OPEN':
                if opening is not None or q!=0 or trade['fee']!=0:raise ValueError('Invalid missing-open cancellation')
                continue
            if q<=0 or not float(q).is_integer():raise ValueError('Invalid market quantity')
            near(trade['price'],opening,'raw open');near(trade['fee'],q*opening*cost,'fee')
            sign=1 if side=='BUY' else -1
            shares[t]=shares.get(t,0)+sign*q
            if shares[t]<-1e-8:raise ValueError('Sold unheld shares')
            if abs(shares[t])<1e-9:del shares[t]
            cash-=sign*q*opening+trade['fee'];fees+=trade['fee'];checked+=1
            if name=='strategy':participation.append({'date':day,'ticker':t,'quantity':q,
                'fraction_of_full_day_volume':q/bars[t][2] if bars[t][2]>0 else None})
        if cash<-.000001:raise ValueError('Borrowed cash')
        near(cash,new['cash'],'cash');near(fees,new['fees'],'cumulative fees')
        if shares.keys()!=new['shares'].keys():raise ValueError('Wrong held symbols')
        for t,q in shares.items():near(q,new['shares'][t],'held quantity')
        normalize=lambda rows:sorted((c['ticker'],c['reason'],str(c['pay_date']),round(c['amount'],6),round(c.get('maximum_amount',0),6)) for c in rows)
        if normalize(claims)!=normalize(new['receivables']):raise ValueError('Unreconciled cash claims')
        stock=sum(q*bars[t][1] for t,q in shares.items());receivables=sum(c['amount'] for c in claims)
        row=new['equity'][-1]
        for field,value in [('cash',cash),('stock_value',stock),('receivables',receivables),('nav',cash+stock+receivables),('fees_cumulative',fees)]:near(row[field],value,field)
    return {'status':'PASS','new_sessions':1,'market_trade_rows_checked':checked,'volume_participation':participation,
            'scope':'Independent one-session cash/share/event/fill/fee/mark reconstruction in all four accounts; daily volume is not opening depth.'}


def build(record,previous,cache,engine,policy,steps=None,now=None,verify_git=True):
    now=now or datetime.now(timezone.utc);root=Path(record);old_root=Path(previous)
    errors=[];checks={}
    decision=read(root/'Momentum_core_decision.json',{})
    identity=read(root/'Momentum_core_paper_identity.json',{})
    checkpoint=read(root/'Momentum_core_paper_checkpoint.json')
    old_checkpoint=read(old_root/'Momentum_core_paper_checkpoint.json')
    readiness=read(root/'H3_readiness.json',{})
    for name,state in (steps or {}).items():
        if state in ('failure','cancelled'):errors.append('Workflow step '+name+': '+state)
    if decision.get('status')=='DATA_BLOCKED':errors.append(str(decision.get('error','Frozen journal blocked')))
    try:
        if verify_git:checks['source']=verify_source(engine,policy)
        verify_policy(policy)
        if identity.get('source_fingerprint')!=policy['source_fingerprint'] or identity.get('cohort')!=policy['cohort']:raise ValueError('Unexpected frozen paper identity')
        if decision.get('model')!=policy['model']:raise ValueError('Unexpected paper model')
        if decision.get('live_approved') or decision.get('broker_orders_enabled'):raise ValueError('Live flags must be false')
        old_identity=read(old_root/'Momentum_core_paper_identity.json')
        if old_identity and identity!=old_identity:raise ValueError('Original paper identity changed')
        if errors:raise ValueError('Required processing step did not complete')
        if old_checkpoint and not checkpoint:raise ValueError('Accepted checkpoint disappeared')
        if checkpoint:
            sessions=prefix(old_checkpoint,checkpoint,policy)
            checks['prefix']={'status':'PASS','sessions':len(sessions),'accounts':4}
            checks['accounting']=audit_delta(old_checkpoint,checkpoint,cache,read(root/'Momentum_core_inputs.json',{}),facts(engine))
        else:
            if now>datetime.fromisoformat(policy['first_checkpoint_deadline_utc']):raise ValueError('Original prospective bootstrap deadline missed')
            if decision.get('status')!='PAPER_WAITING_FOR_SESSIONS':raise ValueError('No accepted checkpoint')
            checks['prefix']={'status':'WAITING','sessions':0,'accounts':4}
    except Exception as exc:
        errors.append(str(exc))
        # Never show an unreconciled new observation as accepted performance.
        checkpoint=old_checkpoint if old_checkpoint and checks.get('source',{}).get('status')=='PASS' else None
    if readiness.get('status')=='DATA_BLOCKED':errors.append(readiness.get('error','Required market access failed'))
    wf=read(root/'H3_workflow.json',{})
    if wf and wf.get('state')!='active':errors.append('Scheduled workflow is not active')
    metrics_by_cost={};gate_results={}
    for cost,s,b in [('15bp','strategy','benchmark'),('30bp','stress_strategy','stress_benchmark')]:
        value=metrics(checkpoint[s],checkpoint[b],policy['minimum_periods']) if checkpoint else None
        metrics_by_cost[cost]=value;gate_results[cost]=gates(value,policy)
    m=metrics_by_cost['15bp'];periods=m['Periods'] if m else 0
    mature=periods>=policy['minimum_periods']
    financial=mature and all(g['pass'] for checks in gate_results.values() for g in checks)
    validation='DATA_BLOCKED' if errors else 'COLLECTING' if not mature else 'FORWARD_PASS_REVIEW_REQUIRED' if financial else 'FORWARD_NO_GO'
    accepted=checkpoint['strategy'] if checkpoint else None
    holdings=[];last=accepted['last_date'] if accepted else None
    old_snapshot=read(old_root/'H3_snapshot.json',{})
    bars=read(Path(cache)/'raw-v1'/f'{last}.json.gz',{}).get('bars',{}) if last else {}
    old_positions={r['ticker']:r for r in old_snapshot.get('holdings',[])}
    for t,q in (accepted['shares'].items() if accepted else []):
        price=bars.get(t,[None,None])[1]
        if price is None and old_snapshot.get('as_of')==last:price=old_positions.get(t,{}).get('mark_usd')
        value=q*price if price is not None else None
        holdings.append({'ticker':t,'quantity':q,'mark_usd':price,'value_usd':value,
                         'weight_pct':100*value/accepted['equity'][-1]['nav'] if value is not None else None,
                         'sleeve':'SPY-kärna' if t=='SPY' else 'Momentum','fractional_entitlement':not float(q).is_integer()})
    historical_register=read(Path(engine)/'docs/CORE_PORTFOLIO_H3_RESULTS_20261029.json',{})
    historical=next((a for a in historical_register.get('attempts',[]) if a['phase']=='extension' and a['delay']==5 and a['cost']==.0015 and a['halt_mark_policy']=='last_quote'),{})
    actual_metrics=metrics(accepted,checkpoint['benchmark'],10**6) if accepted else None
    operational='DATA_BLOCKED' if errors else decision.get('status','UNAVAILABLE')
    snapshot={'schema_version':1,'model':policy['model'],'cohort':policy['cohort'],'source_fingerprint':policy['source_fingerprint'],
              'generated_at':now.isoformat(),'as_of':last,'status':operational,'live_approved':False,'broker_orders_enabled':False,
              'sessions':len(accepted['equity']) if accepted else 0,'metrics':actual_metrics,'cost_cases':metrics_by_cost,
              'cash_usd':accepted['cash'] if accepted else None,'receivables_usd':sum(c['amount'] for c in accepted['receivables']) if accepted else None,
              'holdings':holdings,'latest_decision':accepted['targets'][-1] if accepted and accepted['targets'] else None,
              'pending_intentions':accepted['pending'] if accepted and not errors else None,
              'recent_trades':accepted['trades'][-12:] if accepted else [],
              'curve':[{'date':a['date'],'nav':a['nav'],'spy_nav':b['nav']} for a,b in zip(accepted['equity'],checkpoint['benchmark']['equity'])] if accepted else [],
              'validation':{'status':validation,'observed_periods':periods,'required_periods':policy['minimum_periods'],
                            'remaining_periods':max(0,policy['minimum_periods']-periods),'period_unit':policy['period_unit'],
                            'earliest_assessment_month':policy['earliest_full_assessment_month'],'financial_gates_passed':financial,
                            'gates':gate_results,'automatic_live_go_allowed':False,'explicit_user_approval_required':True},
              'execution':{'fees_model_bps':[15,30],'spread_status':'UNVERIFIED','opening_depth_status':'UNVERIFIED',
                           'actual_broker_fees_status':'NOT_OBSERVED','live_readiness':'INDEPENDENT_EXECUTION_REVIEW_REQUIRED',
                           'quote_access':(readiness if readiness.get('live_probe') else readiness.get('last_live_probe') or {}).get('optional_quotes'),
                           'liquidity':checks.get('accounting',{}).get('volume_participation',[]),
                           'note':'Daglig öppningskurs och 15/30 bp är simulerade antaganden. Daglig volym verifierar inte likviditeten i öppningsauktionen.'},
              'operations':{'errors':errors,'checks':checks,'readiness':readiness,'workflow':wf,
                            'next_expected_attempt_at':next_attempt(now),'delay_grace_minutes':policy['monitor_delay_grace_minutes'],
                            'workflow_run':os.getenv('GITHUB_RUN_ID'),'workflow_attempt':os.getenv('GITHUB_RUN_ATTEMPT')},
              'schedule':{'cron_utc':'35 0,3,6,9 * * 2-6','first_expected_attempt_at':policy['first_scheduled_attempt_utc'],
                          'initial_deadline_at':policy['first_checkpoint_deadline_utc']},
              'historical':{'label':'Historiskt backtest, inte paper trading','evidence_class':'DEVELOPMENT_RESEARCH',
                            'start':'2024-01-01','end':'2026-10-28','metrics':historical.get('metrics'),'status':'PAPER_ONLY'}}
    return snapshot


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('record-dir','previous-dir','cache-dir','engine-dir','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--policy',default='h3_forward_policy.json');p.add_argument('--steps',default='{}');a=p.parse_args()
    policy=read(a.policy);result=build(a.record_dir,a.previous_dir,a.cache_dir,a.engine_dir,policy,json.loads(a.steps))
    record=Path(a.record_dir);record.mkdir(parents=True,exist_ok=True)
    if result['validation']['observed_periods']>=policy['minimum_periods'] and not result['operations']['errors']:
        fixed={'cohort':policy['cohort'],'source_fingerprint':policy['source_fingerprint'],
               'cost_cases':result['cost_cases'],'gates':result['validation']['gates'],
               'financial_gates_passed':result['validation']['financial_gates_passed'],
               'live_approved':False,'broker_orders_enabled':False}
        first=record/'H3_first_30_period_verdict.json'
        if first.exists() and read(first)!=fixed:
            result['operations']['errors'].append('The first complete validation verdict changed')
            result['status']=result['validation']['status']='DATA_BLOCKED';result['pending_intentions']=None
        if not first.exists():first.write_text(json.dumps(fixed,indent=2,allow_nan=False))
    if result['operations']['errors']:
        # Quarantine only the new attempt; never advance the accepted prefix on
        # independent rejection or a failed required processing/storage step.
        previous=Path(a.previous_dir)
        current_files=list(record.glob('Momentum_core_*'))
        with tarfile.open(record/'H3_rejected_attempt.tar.gz','w:gz') as archive:
            for file in current_files:archive.add(file,arcname=file.name)
        for file in current_files:
            if file.name=='Momentum_core_paper_identity.json':continue
            original=previous/file.name
            if original.exists():shutil.copyfile(original,file)
            else:file.unlink()
        blocked={'model':policy['model'],'cohort':policy['cohort'],'status':'DATA_BLOCKED',
                 'error':'; '.join(result['operations']['errors']),'live_approved':False,'broker_orders_enabled':False}
        (record/'Momentum_core_decision.json').write_text(json.dumps(blocked,indent=2))
        (record/'Momentum_core_paper_orders.json').write_text(json.dumps(dict(blocked,intentions_for_next_observed_session=None),indent=2))
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(text)
    (record/'H3_snapshot.json').write_text(text)
    (record/'H3_validation_report.json').write_text(json.dumps(result['validation'],indent=2,allow_nan=False))
    lines=['# H3 forward validation', '',f"Status: {result['validation']['status']}",f"Accepted as of: {result['as_of']}",
           f"Observed sessions: {result['sessions']}",f"Complete monthly periods: {result['validation']['observed_periods']}/30",'',
           'No live GO or broker orders. Historical results are excluded from the forward sample.', '',
           '| Cost | Gate | Value | Pass |','|---|---|---:|---|']
    for cost,items in result['validation']['gates'].items():
        lines += [f"| {cost} | {g['gate']} | {g['value']} | {g['pass']} |" for g in items]
    lines += ['',result['execution']['note'],'Spread, opening depth and actual brokerage fees remain unverified.']
    (record/'H3_validation_report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'status':result['status'],'validation':result['validation']['status'],'sessions':result['sessions'],'errors':result['operations']['errors']}))
    if result['operations']['errors']:raise SystemExit(1)


if __name__=='__main__':main()
