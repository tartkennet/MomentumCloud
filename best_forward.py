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
import best_strategy as strategy
import best_capital as capital
import audit_best as audit

VERSION='best-signal-v1'


def reference(row,day,cache,client):
    path=cache/'best-reference-v1'/day/(row['ticker']+'.json')
    if path.exists():receipt=read_json(path)
    else:
        raw=client.get('/v3/reference/tickers/'+row['ticker'],{'date':day})['results']
        payload={k:raw.get(k) for k in ('ticker','cik','sic_code','type','primary_exchange','name')}
        receipt=dict(date=day,observed_at=datetime.now(timezone.utc).isoformat(),results=payload)
        atomic_json(path,receipt)
    d=receipt['results']
    if receipt['date']!=day or d['ticker']!=row['ticker'] or str(d['cik']).zfill(10)!=row['cik'] or d['type']!='CS':
        raise ValueError('REFERENCE_IDENTITY_MISMATCH')
    sic=str(d.get('sic_code') or '').zfill(4)
    try:sector=strategy.division(sic)
    except (ValueError,TypeError):
        evidence=receipt.get('sic_evidence')
        if not evidence:
            filings=client.get('/v1/reference/sec/filings',{'entities.company_data.ticker':row['ticker'],
                'filing_date.lte':day,'sort':'filing_date','order':'desc','limit':20}).get('results',[])
            for filing in filings:
                filed=iso_date(filing.get('filing_date',''))
                try:datetime.fromisoformat(filed)
                except ValueError:continue
                if filed>day:continue
                for entity in filing.get('entities',[]):
                    company=entity.get('company_data',{})
                    if entity.get('relation')!='filer' or str(company.get('cik','')).zfill(10)!=row['cik']:continue
                    candidate=str(company.get('sic') or '').zfill(4)
                    try:strategy.division(candidate)
                    except (ValueError,TypeError):continue
                    evidence=dict(sic=candidate,cik=row['cik'],filed=filed,accession=filing.get('accession_number') or filing.get('id'),
                        observed_at=datetime.now(timezone.utc).isoformat(),source='DATED_PROVIDER_SEC_FILER_REFERENCE',
                        source_sha256=digest(filing))
                    break
                if evidence:break
            if evidence:
                receipt['sic_evidence']=evidence;atomic_json(path,receipt)
        if not evidence or evidence['filed']>day or evidence['cik']!=row['cik']:
            raise ValueError('UNVERIFIED_INDUSTRY_CLASSIFICATION_'+row['ticker'].replace('.','_').replace('-','_')+'_SIC_'+sic)
        sic=evidence['sic'];sector=strategy.division(sic)
    return dict(row,sic=sic,industry=sic[:2],division=sector,reference_sha256=digest(receipt))



def collect(data,client,cache,previous,now,output=None):
    day=data.sessions[-1]
    if (now.date()-datetime.fromisoformat(day).date()).days>4:raise ValueError('STALE_MARKET_PRICES')
    rows,diagnostics,on=strategy.collect_prices(data,day,cache)
    population_audit=audit.population(data,day,rows)
    spy=closes_at(data,day,'SPY',253)
    for r in rows:audit.price_metrics(r,closes_at(data,day,r['ticker'],253),spy)
    if output:
        atomic_json(Path(output)/'best-coverage.json',dict(price_as_of=day,diagnostics=diagnostics,population_audit=population_audit,ranked_liquid=[{k:v for k,v in r.items() if k!='returns63'} for r in rows]))
    strong=[r for r in rows if r['strong']][:40]
    with ThreadPoolExecutor(max_workers=4) as pool:
        pool_rows=list(pool.map(lambda row:reference(row,day,cache,BestProvider()),strong))
    edges=strategy.clusters(pool_rows);targets,skips=strategy.select(pool_rows)
    analysis=dict(ranked_liquid=[{k:v for k,v in r.items() if k!='returns63'} for r in rows],strong_pool=pool_rows,targets=targets)
    checked=audit.signal(analysis)
    month=datetime.now(timezone.utc).astimezone(NY).strftime('%Y-%m')
    old=previous.get('signal',{}).get('selection') if previous else None
    selection=old if old and old['month']==month else None
    if not selection and on and len(targets)==10:
        selection=dict(month=month,as_of=day,observed_at=datetime.now(timezone.utc).isoformat(),rows=targets)
    bars=data.bars(day);ids={r['ticker']:str(r.get('cik','')).zfill(10) for r in data.universe(day) if core.eligible(r)}
    wanted={r['ticker'] for r in selection['rows']} if selection else set()
    quotes={t:bars[t][1] for t in wanted if bars.get(t) and core.number(bars[t][1])}
    if selection:
        for row in selection['rows']:
            if ids.get(row['ticker'])!=row['cik']:quotes.pop(row['ticker'],None)
    provenance=dict(price_inputs_sha256=data.input_fingerprint(),reference_hashes={r['ticker']:r['reference_sha256'] for r in pool_rows},
        protocol_fingerprint=strategy.fingerprint(),source_commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),preregistration_commit='19e40bc645ce5f34ff06e870338b9515ca81fda5',
        source_files={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ('best_strategy.py','best_data.py','best_inventory.py','best_capital.py','best_forward.py','audit_best.py',strategy.PROTOCOL)})
    snapshot=dict(version=VERSION,market_verified=True,selection_verified=checked['status']=='PASS',quotes_as_of=day,
                  selection=selection,quotes=quotes,coverage=1.,provenance=provenance)
    return dict(model=strategy.MODEL,generated_at=datetime.now(timezone.utc).isoformat(),price_as_of=day,risk_on=on,
        diagnostics=diagnostics,population_audit=population_audit,signal_audit=checked,formation_skips=skips,correlation_edges=edges,
        provenance=provenance,signal=snapshot,**analysis)


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
    p['sha256']=digest(p);state['pending']=p;state['decisions'].append(copy.deepcopy(p));state['previous_risk']=on


def initialize(report,now,requested=''):
    selection=report['signal'].get('selection')
    if not report['risk_on'] or not selection or len(selection['rows'])!=10:raise ValueError('AWAITING_VALID_STRONG_FORMATION')
    rows=copy.deepcopy(selection['rows'])
    for r in rows:r['price_usd']=report['signal']['quotes'][r['ticker']]
    required=capital.requirements(rows,report['fx']['usdsek']);audit.funding(rows,report['fx']['usdsek'],required)
    initial=required['minimum_capital_sek'] if not requested or requested=='AUTO_MINIMUM' else float(requested)
    if not math.isfinite(initial) or initial<=0 or abs(initial*100-round(initial*100))>1e-5:raise ValueError('INVALID_INITIAL_CAPITAL')
    config=dict(policy='BEST_CAPITAL_V1',mode='AUTO_MINIMUM' if not requested or requested=='AUTO_MINIMUM' else 'EXPLICIT',
        initial_sek=initial,configured_at=now.isoformat(),funding=required,selection_sha256=digest(selection),fx=report['fx'])
    state=bootstrap(dict(initial_usd=initial/report['fx']['usdsek'],fx=report['fx']),strategy.fingerprint(),now)
    state.update(initial_sek=initial,opening_quotes=[],valuation_fx={},trade_fx={},capital_configuration=config,cohort_id=digest(config))
    return state


def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True);prev=Path(args.previous)
    prior=read_json(prev/'best-state.json') if (prev/'best-state.json').exists() else None
    previous=read_json(prev/'best-report.json') if (prev/'best-report.json').exists() else {}
    report=None
    try:
        data,client=data_for(Path(args.cache),datetime.now(timezone.utc))
        report=collect(data,client,Path(args.cache),previous,datetime.now(timezone.utc),out)
        rates=ecb_rates();fx=rate_on(rates,report['price_as_of'])
        if not fx:raise ValueError('NO_VERIFIED_INITIAL_FX')
        report.update(fx=fx,fx_history=rates,errors=[])
        state=copy.deepcopy(prior) if prior else initialize(report,datetime.now(timezone.utc),os.environ.get('BEST_INITIAL_SEK',''))
        if state['model_fingerprint']!=strategy.fingerprint():raise ValueError('FROZEN_BEST_PROTOCOL_CHANGED')
        decide(state,report,data,datetime.now(timezone.utc))
        state=observe_account(state,data,client,datetime.now(timezone.utc))
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
            for f in ('decisions','event_journal','opening_quotes'):assert state[f][:len(prior[f])]==prior[f]
        state['previous_state_sha256']=digest(prior) if prior else None
        paper=ledger_summary(state,report['signal'],datetime.now(timezone.utc))
        paper.update(model=strategy.MODEL,policy=strategy.PARAMETERS,experiment_label='PAPER_EXPERIMENT',
                     economic_status='NO_GO_INSUFFICIENT_EVIDENCE',historical_go_required_for_paper=False)
        checked=audit.account(state,paper);paper['statistics_audit']=checked
        report.update(paper=paper,technical_readiness=dict(status='PASS',signal=report['signal_audit'],account=checked,
            funded=not state.get('blockers'),membership_count=len((report['signal'].get('selection') or {}).get('rows',[]))))
        atomic_json(out/'best-state.json',state)
    except Exception as exc:
        report=copy.deepcopy(previous) if prior else report if report else dict(model=strategy.MODEL,signal={})
        if (out/'best-coverage.json').exists() and not prior:
            coverage=read_json(out/'best-coverage.json');report.update(coverage)
        if 'paper' not in report:report['paper']=dict(model=strategy.MODEL,mode='PAPER_ONLY',
            experiment_label='PAPER_EXPERIMENT',live_approved=False,broker_orders_enabled=False,paper_started=False,initial_sek=None,
            positions=[],trades=[],curve=[],status='BLOCKED')
        report.update(generated_at=datetime.now(timezone.utc).isoformat(),technical_readiness=dict(status='BLOCKED'),
                      errors=[str(exc) if __import__('re').fullmatch(r'[A-Z][A-Z0-9_]{0,100}',str(exc)) else type(exc).__name__])
        report['paper'].update(status='BLOCKED',blockers=report['errors'])
        if prior:
            prior['previous_state_sha256']=digest(prior);report['paper']['journal_sha256']=digest(prior)
            atomic_json(out/'best-state.json',prior)
    atomic_json(out/'best-report.json',report)
    summary=dict(status=report['technical_readiness']['status'],paper_status=report['paper']['status'],
        initial_sek=report['paper'].get('initial_sek'),targets=[r['ticker'] for r in (report.get('signal',{}).get('selection') or {}).get('rows',[])],errors=report.get('errors',[]),coverage={k:report.get('diagnostics',{}).get(k) for k in ('reference_records','priced_liquid','strong')})
    print('BEST_RESULT',json.dumps(summary),flush=True)
    if os.environ.get('GITHUB_ACTIONS')=='true':print('::notice title=BEST verification::'+json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cache','previous','output'):p.add_argument('--'+name,required=True)
    run(p.parse_args())
