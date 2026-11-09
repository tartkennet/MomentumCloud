"""One user-selected simulation, historical initialization followed by prospective E2 only."""
import argparse,copy,hashlib,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path
from quality_forward import bootstrap,digest
from momentum_core_data import atomic_json,read_json
from h3_display import ecb_rates,rate_on
from avanza10_forward import summarize
import best_v2_forward as controller
import best_v2_execution as execution
import best_v2_strategy as strategy
from best_data import data_for
from audit_best_v2_user import audit_account,validate_seed

ACCOUNT='best-v2-user-simulation-2026-11-09'
SEED=Path('data/best-v2-user-start.json')

def initialize(source,report,now):
    validate_seed(source)
    fx=dict(date=source['signal_day'],usdsek=source['fx_rate_sek_per_usd'],source=source['fx_source'])
    state=bootstrap(dict(initial_usd=25000/fx['usdsek'],fx=fx),strategy.fingerprint(),datetime.fromisoformat('2026-11-09T14:30:00+00:00'))
    state.update(account_id=ACCOUNT,initial_sek=25000,source_start=copy.deepcopy(source),source_start_sha256=digest(source),
        registered_at=now.isoformat(),initialization_kind='SIMULATED_HISTORICAL_INITIALIZATION',
        opening_quotes=[],valuation_fx={},trade_fx={},decision_month='2026-11',previous_risk=True,risk_on=True,
        capital_configuration=dict(policy='USER_SELECTED_SIMULATED_START',mode='EXPLICIT',initial_sek=25000,configured_at=now.isoformat()),cohort_id=ACCOUNT)
    s=state['strategy'];prices={}
    names={r['ticker'] for r in report['signal']['selection']['rows']}
    if names!={h['ticker'] for h in source['holdings']}:raise ValueError('START_MEMBERS_DIFFER_FROM_VERIFIED_SELECTION')
    for h in source['holdings']:
        q=h['quantity'];n=q*h['open_usd'];cost=max(1,n*.0025)+n*.004
        s['cash']-=n+cost;s['fees']+=cost;s['shares'][h['ticker']]=q;prices[h['ticker']]=h['mark_usd']
        s['trades'].append(dict(date=source['trade_day'],ticker=h['ticker'],side='BUY',quantity=q,price=h['open_usd'],fee=cost,
            initialization_kind=state['initialization_kind'],execution_at=None,price_as_of='2026-11-09T14:30:00+00:00',
            quote_observed_at=source['mark_observed_at'],recorded_at=now.isoformat(),source_sha256=digest(source),
            actual_execution=False,original_limit_override=h['ticker']=='FIGS'))
    stock=sum(s['shares'][t]*p for t,p in prices.items())
    s['equity'].append(dict(date=source['mark_date'],nav=s['cash']+stock,cash=s['cash'],stock_value=stock,receivables=0,positions=10,fees_cumulative=s['fees']))
    state['valuation_quotes'][source['mark_date']]=dict(observed_at=source['mark_observed_at'],prices=prices,shares=copy.deepcopy(s['shares']),source_kind=state['initialization_kind'])
    state['valuation_fx'][source['mark_date']]=fx;state['trade_fx'][source['trade_day']]=fx
    state['capital_configuration']['source_sha256']=digest(source)
    return state

def export(state,report,now):
    checked=audit_account(state);state['audits']={'strategy':checked}
    paper=summarize(state,report['signal'],now)
    paper.update(model=strategy.MODEL,policy=strategy.PARAMETERS,account_id=ACCOUNT,initialization_kind=state['initialization_kind'],registered_at=state['registered_at'],
        first_trade_at=None,historical_start_date='2026-11-09',historical_start_count=10,
        historical_start_notice='Historiskt rekonstruerad fiktiv start vald av användaren. Inte exekverade order. FIGS ingår trots överskriden ursprunglig köpgräns.',
        initialization_source_sha256=state['source_start_sha256'],execution_policy=state['execution_policy'],
        execution_attempts=state.get('execution_attempts',[])[-12:],last_missed_execution=next((g for g in reversed(state['gaps']) if g['kind']=='MISSED_OPEN_NO_BACKFILL'),None),trading_outcome=state.get('execution_outcome') or dict(status='MONITORING',filled=0,orders=[]),
        prospective_trade_count=sum(not t.get('initialization_kind') for t in state['strategy']['trades']),
        experiment_label='PAPER_EXPERIMENT',journal_sha256=digest(state),historical_go_required_for_paper=False)
    metadata={r['ticker']:r for r in report['signal']['selection']['rows']}
    for p in paper['positions']:
        row=metadata.get(p['ticker'],{});p.update(name=row.get('name',p['ticker']),sector=row.get('sector'),factor=row.get('factor'))
    paper['audits']={'strategy':checked};paper['statistics_audit']=checked
    paper['sector_actual_distribution']=[dict(sector=sector,stocks=sum(p['sector']==sector for p in paper['positions']),value_sek=sum(p['value_sek'] or 0 for p in paper['positions'] if p['sector']==sector),weight_pct=100*sum(p['value_sek'] or 0 for p in paper['positions'] if p['sector']==sector)/paper['nav_sek'] if paper['nav_sek'] else None) for sector in sorted({p['sector'] for p in paper['positions'] if p['sector']})]
    report.update(paper=paper,account_id=ACCOUNT,technical_readiness=dict(status='PASS',signal=report.get('signal_audit'),funded=not state.get('blockers'),account=checked),errors=[])
    return report

def run(args):
    out=Path(args.output);out.mkdir(exist_ok=True,parents=True);priorpath=Path(args.previous)/'best-v2-state.json'
    prior=read_json(priorpath) if priorpath.exists() else None
    previous=read_json(Path(args.previous if prior else args.formation)/'best-v2-report.json')
    now=datetime.now(timezone.utc);source=read_json(SEED)
    try:
        data,client=data_for(Path(args.cache),now)
        report=controller.collect(data,client,Path(args.cache),previous,now,out)
        rates=ecb_rates();fx=rate_on(rates,report['price_as_of'])
        if not fx:raise ValueError('MISSING_VERIFIED_FX')
        report.update(fx=fx,fx_history=rates,operations_proof=operations(),errors=[])
        state=copy.deepcopy(prior) if prior else initialize(source,report,now)
        if state['account_id']!=ACCOUNT or state['source_start_sha256']!=digest(source):raise ValueError('IMMUTABLE_USER_START_CHANGED')
        if not prior:
            bars=data.bars(source['trade_day'])
            for h in source['holdings']:
                if abs(bars[h['ticker']][0]-h['open_usd'])>1e-7 or abs(bars[h['ticker']][1]-h['mark_usd'])>1e-7:raise ValueError('START_SOURCE_PRICE_MISMATCH')
        execution.register(state,data,now)
        controller.decide(state,report,data,now)
        state=execution.observe(state,data,client,now)
        for day in {r['date'] for r in state['strategy']['equity']}|{t['date'] for t in state['strategy']['trades']}:
            if day not in state['valuation_fx']:
                rate=rate_on(rates,day)
                if not rate:raise ValueError('MISSING_DATED_FX')
                state['valuation_fx'][day]=rate
            state['trade_fx'].setdefault(day,rate_on(rates,day))
        controller.decide(state,report,data,datetime.now(timezone.utc))
        state['previous_state_sha256']=digest(prior) if prior else None
        report=export(state,report,datetime.now(timezone.utc))
        atomic_json(out/'best-v2-state.json',state);atomic_json(out/'best-v2-report.json',report)
        print('USER_PAPER_VERIFIED',json.dumps(dict(account=ACCOUNT,holdings=len(state['strategy']['shares']),cash_sek=report['paper']['cash_sek'],nav_sek=report['paper']['nav_sek'],trades=len(state['strategy']['trades']),pending=bool(state.get('pending')))))
    except Exception:
        if prior:
            previous.update(generated_at=now.isoformat(),errors=['USER_ACCOUNT_COLLECTION_FAILED'],technical_readiness={'status':'BLOCKED'})
            previous['paper'].update(status='BLOCKED',blockers=['USER_ACCOUNT_COLLECTION_FAILED'])
            prior['previous_state_sha256']=digest(prior)
            previous['paper']['journal_sha256']=digest(prior)
            atomic_json(out/'best-v2-state.json',prior);atomic_json(out/'best-v2-report.json',previous)
        raise

def operations():
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if os.getenv('GITHUB_EVENT_NAME')=='pull_request':return dict(enabled=False,source_commit=sha,validation_only=True)
    workflow=json.loads(subprocess.check_output(['gh','api','repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/workflows/best_v2_user.yml'],text=True))
    if workflow['state']!='active' or os.getenv('GITHUB_REF')!='refs/heads/main':raise ValueError('USER_AUTOMATION_NOT_ACTIVE')
    return dict(enabled=True,source_commit=sha,workflow_state='active',workflow_id=workflow['id'],verified_at=datetime.now(timezone.utc).isoformat())

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cache','previous','formation','output'):p.add_argument('--'+name,required=True)
    run(p.parse_args())
