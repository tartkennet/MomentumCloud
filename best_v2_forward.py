"""Independent BEST prospective experiment; never reads a prior model's account."""
import argparse
import copy
import hashlib
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path

import momentum_core as core
from momentum_core_data import atomic_json,read_json
from quality_forward import NY,bootstrap,digest
from quality_sources import Provider,DataUnavailable,iso_date
from best_data import data_for,BestProvider
from avanza10_forward import observe_account,summarize as ledger_summary
from h3_display import ecb_rates,rate_on
from research_stocks10 import fee
from audit_core_normalized import closes_at
import best_v2_strategy as strategy
import best_v2_capital as capital
import audit_best_v2 as audit
import best_v2_execution as execution

VERSION='best-signal-v2'


from best_v2_sources import reference as economic_reference

def reference(row,day,cache,client):
    try:
        r=economic_reference(row,day,cache,client,datetime.now(timezone.utc).isoformat())
        print('BEST_V2_REFERENCE',json.dumps(dict(ticker=r['ticker'],sector=r['sector'],status=r['event_status'])),flush=True)
        return r
    except DataUnavailable as exc:
        print('BEST_V2_REFERENCE_BLOCK',json.dumps(dict(ticker=row['ticker'],reason=str(exc))),flush=True)
        raise


def locked_member_references(rows,selection,day,cache):
    current={r['ticker']:r for r in rows};verified=[]
    for member in selection['rows']:
        row=current.get(member['ticker'])
        if not row or row['cik']!=member['cik']:raise ValueError('COMMITTED_MEMBER_PRICE_OR_LIQUIDITY_UNVERIFIED')
        checked=reference(row,day,cache,BestProvider())
        if checked['event_status']!='CLEAR':raise ValueError('COMMITTED_MEMBER_CORPORATE_EVENT_BLOCKED')
        verified.append(checked)
    if len(verified)!=10:raise ValueError('TEN_VERIFIED_COMMITTED_MEMBERS_REQUIRED')
    return verified


def collect(data,client,cache,previous,now,output=None):
    day=data.sessions[-1]
    if (now.date()-datetime.fromisoformat(day).date()).days>4:raise ValueError('STALE_MARKET_PRICES')
    rows,diagnostics,on=strategy.collect_prices(data,day,cache)
    from collections import Counter
    diagnostics['price_filters']=dict(Counter(code for r in rows for code in r['price_exclusions']))
    print('BEST_V2_PRICE_FILTERS',json.dumps(diagnostics['price_filters']),flush=True)
    diagnostics['requested_event_examples']=[dict(ticker=r['ticker'],strong=r['strong'],vol63=r['vol63'],price_exclusions=r['price_exclusions']) for r in rows if r['ticker'] in ('ITGR','HZO')]
    print('BEST_V2_REQUESTED_EVENT_EXAMPLES',json.dumps(diagnostics['requested_event_examples']),flush=True)
    population_audit=audit.population(data,day,rows)
    spy=closes_at(data,day,'SPY',253)
    if output:
        atomic_json(Path(output)/'best-v2-coverage.json',dict(price_as_of=day,diagnostics=diagnostics,population_audit=population_audit,ranked_liquid=[{k:v for k,v in r.items() if k!='returns63'} for r in rows]))
    for r in rows:audit.price_metrics(r,closes_at(data,day,r['ticker'],253),spy,[b[1]*b[2] for _,b in data.history(day,r['ticker'],253)[:25]])
    from best_v2_early import rank as early_rank,diagnose
    early_analysis=dict(component='E1_WATCHLIST',active_for_trading=False,ranked=early_rank(rows),app=diagnose(data,'APP',day))
    if output:atomic_json(Path(output)/'best-v2-early.json',early_analysis)
    print('BEST_V2_APP_ANALYSIS',json.dumps({k:v for k,v in early_analysis['app'].items() if k!='history'}),flush=True)
    month=now.astimezone(NY).strftime('%Y-%m')
    old=previous.get('signal',{}).get('selection') if previous else None
    selection=copy.deepcopy(old) if old and old['month']==month else None
    current_references=[]
    if selection:
        # Membership was already frozen prospectively for this month. A new,
        # unheld research candidate cannot block the ten committed issuers.
        # Every committed issuer still needs fresh identity/events/price proof.
        current_references=locked_member_references(rows,selection,day,cache)
        analysis=copy.deepcopy({k:previous[k] for k in ('ranked_liquid','strong_pool','targets')})
        pool_rows=analysis['strong_pool'];targets=analysis['targets']
        edges=previous.get('correlation_edges',[]);skips=previous.get('formation_skips',[])
        diagnostics['classification']=dict(scope='LOCKED_MONTH_MEMBERS',verified=len(current_references),ranking_as_of=selection['as_of'])
    else:
        strong=[r for r in rows if r['strong']][:60]
        pool_rows=copy.deepcopy(strong)
        edges=strategy.clusters(pool_rows);targets=[];skips=[];classified=0
        for index,row in enumerate(pool_rows):
            pool_rows[index]=reference(row,day,cache,BestProvider());classified+=1
            targets,skips=strategy.select(pool_rows[:index+1])
            if len(targets)==10:break
        for row in pool_rows[classified:]:row['classification_status']='NOT_NEEDED_AFTER_TEN_SELECTED'
        diagnostics['classification']=dict(scope='NEW_FULL_UNIVERSE_FORMATION',considered=classified,verified=classified,unneeded_after_ten=len(pool_rows)-classified)
        analysis=dict(ranked_liquid=[{k:v for k,v in r.items() if k!='returns63'} for r in rows],strong_pool=pool_rows,targets=targets)
        current_references=[r for r in pool_rows if r.get('reference_sha256')]
        if on and len(targets)==10:
            selection=dict(month=month,as_of=day,observed_at=now.isoformat(),rows=targets)
    checked=audit.signal(analysis)
    bars=data.bars(day);ids={r['ticker']:str(r.get('cik','')).zfill(10) for r in data.universe(day) if core.eligible(r)}
    wanted={r['ticker'] for r in selection['rows']} if selection else set()
    quotes={t:bars[t][1] for t in wanted if bars.get(t) and core.number(bars[t][1])}
    if selection:
        for row in selection['rows']:
            if ids.get(row['ticker'])!=row['cik']:quotes.pop(row['ticker'],None)
    provenance=dict(price_inputs_sha256=data.input_fingerprint(),reference_hashes={r['ticker']:r['reference_sha256'] for r in current_references},ranking_as_of=selection['as_of'] if selection else day,selection_price_inputs_sha256=previous.get('provenance',{}).get('selection_price_inputs_sha256',previous.get('provenance',{}).get('price_inputs_sha256')) if old and old['month']==month else data.input_fingerprint(),
        protocol_fingerprint=strategy.fingerprint(),source_commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),preregistration_commit='d732489a7940980a01ae52a994fe6a014294b5be',
        source_files={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ('best_v2_strategy.py','best_v2_sources.py','best_data.py','best_inventory.py','best_v2_capital.py','best_v2_forward.py','audit_best_v2.py','best_v2_early.py','best_v2_mirrors.py','data/filing_mirrors.json','best_v2_execution.py',execution.FILE,strategy.PROTOCOL)})
    snapshot=dict(version=VERSION,market_verified=True,selection_verified=checked['status']=='PASS',quotes_as_of=day,
                  selection=selection,quotes=quotes,coverage=1.,provenance=provenance)
    return dict(model=strategy.MODEL,generated_at=datetime.now(timezone.utc).isoformat(),price_as_of=day,risk_on=on,
        diagnostics=diagnostics,population_audit=population_audit,signal_audit=checked,formation_skips=skips,correlation_edges=edges,
        provenance=provenance,signal=snapshot,early_analysis=early_analysis,**analysis)


def cancel(state,now,reason):
    if state.get('pending'):
        state.setdefault('cancelled_intentions',[]).append(dict(observed_at=now.isoformat(),commitment=state['pending']['sha256'],reason=reason))
        state['pending']=None


def decide(state,report,data,now):
    state['blockers']=[];month=now.astimezone(NY).strftime('%Y-%m');on=report['risk_on']
    p=state.get('pending')
    if p and ((not on and p['kind']!='RISK_OFF') or p['created_at'][:7]!=month):cancel(state,now,'RISK_OFF_OR_MONTH_CHANGED')
    state.update(risk_on=on,risk_checked_at=now.isoformat())
    if state.get('pending'):
        if any(o['side']=='BUY' and o['ticker'] not in report['signal']['quotes'] for o in state['pending']['plan']['orders']):
            cancel(state,now,'MISSING_HELD_OR_TARGET_PRICE');state['blockers']=['MISSING_HELD_OR_TARGET_PRICE']
        return
    selection=report['signal'].get('selection')
    breadth=bool(selection and selection['month']==month and len(selection['rows'])==10)
    shares=state['strategy']['shares']
    if not on or not breadth:
        state['previous_risk']=False
        if not on and not shares:return
        if not breadth:state['blockers']=['INSUFFICIENT_STRONG_BREADTH']
        if not shares:return
        if any(q<1 or not float(q).is_integer() for q in shares.values()):
            state['blockers']=['CORPORATE_ENTITLEMENT_REQUIRES_REVIEW'];return
        p=dict(created_at=now.isoformat(),signal_date=report['price_as_of'],targets=[],kind='RISK_OFF',
            plan=dict(orders=[dict(ticker=t,side='SELL',quantity=int(q)) for t,q in sorted(shares.items())]),
            model_fingerprint=state['model_fingerprint'],sources=[digest(report['provenance'])])
    else:
        if state.get('decision_month')==month and state.get('previous_risk') is not False:
            if len(shares)!=10:state['blockers']=['PARTIAL_FILL_REVIEW_REQUIRED']
            return
        rows=copy.deepcopy(selection['rows'])
        try:
            for r in rows:r['price_usd']=report['signal']['quotes'][r['ticker']]
            required=capital.requirements(rows,report['fx']['usdsek']);audit.funding(rows,report['fx']['usdsek'],required)
            state['funding']=dict(required,targets=[dict(r,one_share_cost_cents=required['per_stock_cents'][r['ticker']]) for r in rows])
            nav=state['strategy']['equity'][-1]['nav'] if state['strategy']['equity'] else state['initial_usd']
            if nav*report['fx']['usdsek']+1e-7<required['minimum_capital_sek']:raise ValueError('UNFUNDED_OR_RISK_LIMITED_MINIMUM_BASKET')
            prices={t:data.bars(report['price_as_of'])[t][1] for t in shares}
            plan=capital.orders(rows,shares,nav,state['strategy']['cash'],prices)
            audit.plan(rows,plan,shares,nav,state['strategy']['cash'],prices)
        except (ValueError,KeyError) as exc:
            state['blockers']=[str(exc) if isinstance(exc,ValueError) else 'MISSING_HELD_OR_TARGET_PRICE'];return
        p=dict(created_at=now.isoformat(),signal_date=report['price_as_of'],targets=rows,plan=plan,kind='MEMBERSHIP',
               model_fingerprint=state['model_fingerprint'],sources=[digest(report['provenance'])])
        if not state['benchmark']['trades']:
            limit=data.bars(report['price_as_of'])['SPY'][1]*1.02;q=math.floor(state['benchmark']['cash']/limit)
            while q and q*limit+fee(q*limit)>state['benchmark']['cash']:q-=1
            if q:p['benchmark_order']=dict(quantity=q,limit=limit)
    if state.get('execution_policy'):p['execution_policy']=copy.deepcopy(state['execution_policy'])
    p['sha256']=digest(p);state['pending']=p;state['decisions'].append(copy.deepcopy(p));state['previous_risk']=on


def initialize(report,now,requested=''):
    selection=report['signal'].get('selection')
    if not report['risk_on'] or not selection or len(selection['rows'])!=10:raise ValueError('AWAITING_VALID_STRONG_FORMATION')
    rows=copy.deepcopy(selection['rows'])
    for r in rows:r['price_usd']=report['signal']['quotes'][r['ticker']]
    required=capital.requirements(rows,report['fx']['usdsek']);audit.funding(rows,report['fx']['usdsek'],required)
    initial=max(25000.,required['minimum_capital_sek']) if not requested or requested in ('AUTO_TARGET_25000','AUTO_MINIMUM') else float(requested)
    if not math.isfinite(initial) or initial<=0 or abs(initial*100-round(initial*100))>1e-5:raise ValueError('INVALID_INITIAL_CAPITAL')
    config=dict(policy='BEST_V2_CAPITAL_V1',mode='AUTO_TARGET_25000' if not requested or requested in ('AUTO_TARGET_25000','AUTO_MINIMUM') else 'EXPLICIT',
        initial_sek=initial,configured_at=now.isoformat(),funding=required,selection_sha256=digest(selection),fx=report['fx'])
    state=bootstrap(dict(initial_usd=initial/report['fx']['usdsek'],fx=report['fx']),strategy.fingerprint(),now)
    state.update(initial_sek=initial,opening_quotes=[],valuation_fx={},trade_fx={},capital_configuration=config,cohort_id=digest(config))
    return state


def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True);prev=Path(args.previous)
    prior=read_json(prev/'best-v2-state.json') if (prev/'best-v2-state.json').exists() else None
    previous=read_json(prev/'best-v2-report.json') if (prev/'best-v2-report.json').exists() else {}
    report=None
    try:
        operations=read_json(out/'operations.json') if (out/'operations.json').exists() else None
        if os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_EVENT_NAME')!='pull_request':
            if not operations or not operations.get('enabled') or operations.get('source_commit')!=os.environ.get('GITHUB_SHA'):raise ValueError('V2_AUTOMATION_NOT_VERIFIED')
        data,client=data_for(Path(args.cache),datetime.now(timezone.utc))
        report=collect(data,client,Path(args.cache),previous,datetime.now(timezone.utc),out)
        rates=ecb_rates();fx=rate_on(rates,report['price_as_of'])
        if not fx:raise ValueError('NO_VERIFIED_INITIAL_FX')
        report.update(fx=fx,fx_history=rates,errors=[],operations_proof=operations)
        state=copy.deepcopy(prior) if prior else initialize(report,datetime.now(timezone.utc),os.environ.get('BEST_V2_INITIAL_SEK',''))
        if state['model_fingerprint']!=strategy.fingerprint():raise ValueError('FROZEN_BEST_PROTOCOL_CHANGED')
        execution.register(state,data,datetime.now(timezone.utc),client)
        pending=state.get('pending')
        if pending and pending['kind']=='MEMBERSHIP' and not state['strategy']['trades'] and pending['signal_date']<report['price_as_of']:
            cancel(state,datetime.now(timezone.utc),'PRE_SESSION_REFRESH_VERIFIED_CLOSED_PRICES')
        decide(state,report,data,datetime.now(timezone.utc))
        migration=state.get('execution_migration_members')
        if migration and not state.get('execution_migration_verified') and state.get('pending') and state['pending']['kind']=='MEMBERSHIP':
            if sorted(migration)!=sorted(r['ticker'] for r in state['pending']['targets']):raise ValueError('MIGRATION_CHANGED_TEN_MEMBERS')
            state['execution_migration_verified']=True
        state=execution.observe(state,data,client,datetime.now(timezone.utc))
        for day in {r['date'] for r in state['strategy']['equity']} | {t['date'] for t in state['strategy']['trades']}:
            rate=rate_on(rates,day)
            if not rate:raise ValueError('MISSING_DATED_FX')
            state['valuation_fx'].setdefault(day,rate);state['trade_fx'].setdefault(day,rate)
        decide(state,report,data,datetime.now(timezone.utc))
        state['audits']={k:audit.audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
        if prior:
            assert state['initial_sek']==prior['initial_sek'] and state['capital_configuration']==prior['capital_configuration']
            for k in ('strategy','benchmark'):
                for f in ('trades','equity'):assert state[k][f][:len(prior[k][f])]==prior[k][f]
            for f in ('decisions','event_journal','opening_quotes','gaps','unfilled_orders','cancelled_intentions','execution_attempts','intraday_observations','execution_policy_journal'):
                if f not in prior:continue
                assert state[f][:len(prior[f])]==prior[f]
        state['previous_state_sha256']=digest(prior) if prior else None
        paper=ledger_summary(state,report['signal'],datetime.now(timezone.utc))
        paper.update(model=strategy.MODEL,policy=strategy.PARAMETERS,experiment_label='PAPER_EXPERIMENT',
                     economic_status='NO_GO_INSUFFICIENT_EVIDENCE',historical_go_required_for_paper=False,
                     execution_policy=state.get('execution_policy'),trading_outcome=state.get('execution_outcome'),
                     execution_attempts=state.get('execution_attempts',[])[-12:],
                     last_missed_execution=next((g for g in reversed(state['gaps']) if g['kind']=='MISSED_OPEN_NO_BACKFILL'),None))
        outcome=state.get('execution_outcome') or {}
        if outcome.get('status') in ('OPEN_PRICE_WAITING','OPEN_PRICE_UNAVAILABLE','OPEN_PRICE_PROVIDER_DELAY','MISSED_OPEN_NO_BACKFILL'):
            paper['status']=outcome['status']
        metadata={r['ticker']:r for decision in state['decisions'] for r in decision.get('targets',[])}
        for pos in paper['positions']:pos.update(sector=metadata.get(pos['ticker'],{}).get('sector'),factor=metadata.get(pos['ticker'],{}).get('factor'),healthcare_exposure=metadata.get(pos['ticker'],{}).get('healthcare_exposure'))
        pending=state.get('pending') or {};planned=[]
        if pending.get('kind')=='MEMBERSHIP':
            for row in pending['targets']:
                order=next((o for o in pending['plan']['orders'] if o['ticker']==row['ticker'] and o['side']=='BUY'),None)
                if order:
                    reserve=(order['quantity']*order['limit']+fee(order['quantity']*order['limit']))*state['initial_fx']['usdsek']
                    planned.append(dict(ticker=row['ticker'],sector=row['sector'],factor=row['factor'],quantity=order['quantity'],reserve_sek=reserve,healthcare_exposure=row['healthcare_exposure']))
        sectors=sorted({r['sector'] for r in planned})
        paper['planned_allocations']=planned
        paper['shared_healthcare_exposure']=dict(planned_stocks=sum(x['healthcare_exposure'] for x in planned),reserve_sek=sum(x['reserve_sek'] for x in planned if x['healthcare_exposure']),note='Business/customer exposure can cross economic sector boundaries; this is not a sector reclassification or hard cap.')
        paper['sector_distribution']=[dict(sector=s,stocks=sum(r['sector']==s for r in planned),reserve_sek=sum(r['reserve_sek'] for r in planned if r['sector']==s),weight_pct=100*sum(r['reserve_sek'] for r in planned if r['sector']==s)/state['initial_sek']) for s in sectors]
        paper['sector_actual_distribution']=[]
        if paper['positions'] and all(p.get('sector') and p.get('value_sek') is not None for p in paper['positions']) and paper.get('nav_sek'):
            paper['sector_actual_distribution']=[dict(sector=sector,stocks=sum(p['sector']==sector for p in paper['positions']),value_sek=sum(p['value_sek'] for p in paper['positions'] if p['sector']==sector),weight_pct=100*sum(p['value_sek'] for p in paper['positions'] if p['sector']==sector)/paper['nav_sek']) for sector in sorted({p['sector'] for p in paper['positions']})]
        paper['shared_healthcare_exposure'].update(observed_stocks=sum(bool(p.get('healthcare_exposure')) for p in paper['positions']),observed_value_sek=sum(p['value_sek'] for p in paper['positions'] if p.get('healthcare_exposure')) if paper['sector_actual_distribution'] else None)
        paper['concentration_warnings']=[s['sector'] for s in (paper['sector_actual_distribution'] or paper['sector_distribution']) if s['stocks']>=5 or s['weight_pct']>40]
        checked=audit.account(state,paper);paper['statistics_audit']=checked
        report.update(paper=paper,technical_readiness=dict(status='PASS',signal=report['signal_audit'],account=checked,
            funded=not state.get('blockers'),membership_count=len((report['signal'].get('selection') or {}).get('rows',[]))))
        atomic_json(out/'best-v2-state.json',state)
    except Exception as exc:
        # Emit only code locations, never exception values, URLs or credentials.
        import traceback
        print('BEST_V2_FAILURE_LOCATIONS',json.dumps([dict(file=Path(f.filename).name,line=f.lineno,function=f.name)
            for f in traceback.extract_tb(exc.__traceback__)]),flush=True)
        report=copy.deepcopy(previous) if prior else report if report else dict(model=strategy.MODEL,signal={})
        if (out/'best-v2-coverage.json').exists() and not prior:
            coverage=read_json(out/'best-v2-coverage.json');report.update(coverage)
        if 'paper' not in report:report['paper']=dict(model=strategy.MODEL,mode='PAPER_ONLY',
            experiment_label='PAPER_EXPERIMENT',live_approved=False,broker_orders_enabled=False,paper_started=False,initial_sek=None,
            positions=[],trades=[],curve=[],status='BLOCKED')
        report.update(generated_at=datetime.now(timezone.utc).isoformat(),technical_readiness=dict(status='BLOCKED'),
                      errors=[str(exc) if __import__('re').fullmatch(r'[A-Z][A-Z0-9_]{0,100}',str(exc)) else type(exc).__name__])
        report['paper'].update(status='BLOCKED',blockers=report['errors'])
        if prior:
            prior['previous_state_sha256']=digest(prior);report['paper']['journal_sha256']=digest(prior)
            atomic_json(out/'best-v2-state.json',prior)
    atomic_json(out/'best-v2-report.json',report)
    summary=dict(status=report['technical_readiness']['status'],paper_status=report['paper']['status'],
        initial_sek=report['paper'].get('initial_sek'),planned_allocations=report['paper'].get('planned_allocations',[]),minimum_capital_sek=report['paper'].get('capital_configuration',{}).get('funding',{}).get('minimum_capital_sek'),targets=[r['ticker'] for r in (report.get('signal',{}).get('selection') or {}).get('rows',[])],errors=report.get('errors',[]),coverage={k:report.get('diagnostics',{}).get(k) for k in ('reference_records','priced_liquid','strong')})
    print('BEST_V2_RESULT',json.dumps(summary),flush=True)
    if os.environ.get('GITHUB_ACTIONS')=='true':print('::notice title=BEST verification::'+json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cache','previous','output'):p.add_argument('--'+name,required=True)
    run(p.parse_args())
