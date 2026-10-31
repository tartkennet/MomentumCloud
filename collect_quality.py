"""Bounded current-data collector. No historical fundamental return simulation."""
import argparse
import concurrent.futures
import copy
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path

import momentum_core as core
from momentum_core_data import atomic_json,read_json,paginate
from research_core_actions import supplement
from run_core_risk_research import make_data
from run_core_normalized_research import verify_inputs
from h3_display import ecb_rates
from run_stocks10_research import prior_fx
from quality_sources import Provider,DataUnavailable,current_filing,save_original
from quality_fundamentals import parse_original
from quality_strategy import MODEL,PARAMETERS,choose,plan_orders,division
from quality_audit import audit_fundamental,audit_selection,audit_plan
from audit_core_normalized import closes_at


class PriceProvider(Provider):
    def _get(self,path,params=None):return self.get(path,params)


def extend_events(root,end,client):
    for kind,column in [('splits','execution_date'),('dividends','ex_dividend_date')]:
        paths=sorted(root.glob(kind+'-*-v1.json.gz'),key=lambda p:p.name)
        if not paths:raise DataUnavailable('MISSING_ARCHIVED_EVENTS')
        path=paths[-1];parts=path.name.split('-');start='-'.join(parts[1:4]);previous='-'.join(parts[4:7])
        if previous>=end:continue
        rows=read_json(path)+paginate(client,'/stocks/v1/'+kind,{column+'.gt':previous,column+'.lte':end,'limit':5000,'sort':column+'.asc'})
        atomic_json(root/f'{kind}-{start}-{end}-v1.json.gz',rows)


def market_universe(data,day,nav):
    spy=core.adjusted_history(data,day,'SPY',253)
    if len(spy)!=253:raise DataUnavailable('INCOMPLETE_SPY_HISTORY')
    relative=spy[0]/spy[126];rows=[];reasons=Counter()
    for record in data.universe(day):
        if not core.eligible(record) or record['primary_exchange'] not in ('XNAS','XNYS') or not record.get('cik'):continue
        t=record['ticker'];history=data.history(day,t,253)
        if len(history)!=253 or any(not b for _,b in history):reasons['INCOMPLETE_PRICE_HISTORY']+=1;continue
        p=history[0][1][1]
        if p<10 or p*1.02>nav*.20:reasons['PRICE_OR_WHOLE_LOT']+=1;continue
        adv=sum(b[1]*b[2] for _,b in history[:20])/20
        if adv<20_000_000:reasons['LIQUIDITY']+=1;continue
        c=core.adjusted_history(data,day,t,253)
        if not c:continue
        rs=(c[0]/c[126])/relative-1
        if rs<=0 or c[0]<=sum(c[:200])/200:reasons['NO_PRICE_CONFIRMATION']+=1;continue
        rows.append(dict(ticker=t,cik=str(record['cik']).zfill(10),name=record.get('name',''),price_usd=p,adv20_usd=adv,
            relative_strength=rs,return_6m=c[0]/c[126]-1,price_as_of=day))
    rows.sort(key=lambda r:(-r['adv20_usd'],r['ticker']));unique=[];seen=set()
    for row in rows:
        if row['cik'] in seen:continue
        unique.append(row);seen.add(row['cik'])
        if len(unique)==100:break
    return unique,dict(reasons),spy[0]>sum(spy[:200])/200


def fundamentals(row,cache):
    row=copy.deepcopy(row);provider=Provider()
    try:
        filing,raw=current_filing(provider,row['ticker'],datetime.now(timezone.utc).isoformat())
        observed=datetime.now(timezone.utc).isoformat();receipt=save_original(cache,filing,raw,observed)
        entity=next(e['company_data'] for e in filing['entities'] if e.get('relation')=='filer' and str(e['company_data']['cik']).zfill(10)==row['cik'])
        sic=str(entity.get('sic','')).zfill(4)
        if not sic.isdigit() or not division(sic):row.update(data_status='OUT_OF_SCOPE_INDUSTRY',sic=sic,resolved=True);return row
        f=parse_original(raw,receipt,row['cik'],datetime.now(timezone.utc).isoformat())
        check=audit_fundamental(raw,receipt,f,row['cik'],datetime.now(timezone.utc).isoformat())
        row.update(data_status='VERIFIED',sic=sic,division=division(sic),fundamental=f,fundamental_audit=check,resolved=True)
    except (DataUnavailable,StopIteration,ValueError,AssertionError) as e:
        row.update(data_status='DATA_GAP',reason=str(e) if isinstance(e,DataUnavailable) else type(e).__name__,resolved=False)
    return row


def collect(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True);cache=Path(args.cache)
    report=dict(schema_version=1,model=MODEL,status='COLLECTING',economic_status='NO_GO_INSUFFICIENT_EVIDENCE',
        generated_at=datetime.now(timezone.utc).isoformat(),historical_metrics=None,paper_metrics=None,
        historical_backtest_certified=False,untouched_historical_oos=False,live_approved=False,broker_orders_enabled=False,
        paper_started=False,positions=[],trades=[],sessions=0,initial_sek=20000,parameters=PARAMETERS,errors=[],candidates=[],targets=[])
    atomic_json(out/'quality.json',report)
    try:
        report['original_input_manifest']=verify_inputs(cache,args.manifest)
        now=datetime.now(timezone.utc);end=(now.date()-timedelta(days=1)).isoformat()
        client=PriceProvider();extend_events(cache,end,client)
        # Reuse the authenticated daily raw cache. CoreData fetches only absent
        # raw sessions and the current dated universe; no old strategy replay.
        import run_core_risk_research as adapter
        adapter.PolygonClient=lambda key:client
        data=supplement(make_data(cache,end,False));day=data.sessions[-1]
        if (now.date()-datetime.fromisoformat(day).date()).days>4:raise DataUnavailable('STALE_MARKET_PRICES')
        rates=ecb_rates();fx=prior_fx(rates,now.date().isoformat());nav=20000/fx['usdsek']
        universe,exclusions,risk_on=market_universe(data,day,nav)
        report.update(price_as_of=day,fx=fx,fx_history=rates,risk_on=risk_on,universe_count=len(universe),price_exclusions=exclusions)
        results=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(fundamentals,r,Path(args.fundamentals)):r['ticker'] for r in universe}
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result());report['candidates']=sorted(results,key=lambda r:r['ticker'])
                atomic_json(out/'quality.json',report);print('FUNDAMENTAL',len(results),len(universe),futures[future],results[-1]['data_status'],flush=True)
        valid=[r for r in results if r['data_status']=='VERIFIED']
        coverage=sum(r['resolved'] for r in results)/len(universe) if universe else 0
        targets=choose(valid,nav);selection_check=audit_selection(valid,targets,nav)
        plan=None
        try:plan=plan_orders(targets,{},nav,nav) if targets else None
        except ValueError as e:report['selection_block']=str(e)
        order_check=audit_plan(targets,plan,{},nav,nav,{}) if plan else None
        # Independently recheck every selected price/RS from frozen raw inputs.
        spy=closes_at(data,day,'SPY',253)
        for row in targets:
            c=closes_at(data,day,row['ticker'],253)
            assert math_close(row['relative_strength'],(c[0]/c[126])/(spy[0]/spy[126])-1)
            assert c[0]>sum(c[:200])/200
        permit=len(universe)>0 and coverage>=.90 and len(targets)==10 and risk_on and bool(order_check)
        report.update(generated_at=datetime.now(timezone.utc).isoformat(),coverage=coverage,candidates=sorted(results,key=lambda r:r['ticker']),
            qualified_count=sum(r['fundamental']['qualified'] for r in valid),targets=targets,proposed_orders=plan,
            audits=dict(selection=selection_check,orders=order_check,fundamentals_checked=len(valid)),
            status='PAPER_READY_AWAITING_SESSION' if permit else 'DATA_BLOCKED' if coverage<.9 else 'RISK_OFF' if not risk_on else 'SELECTION_BLOCKED',
            paper_start_permit=permit,initial_usd=nav,
            observations_remaining=30,analyst_revisions='EXCLUDED_NO_VERIFIED_VINTAGES',
            price_mode='LAST_OBSERVED_CLOSE',realtime_verified=False,
            limitations=['No certified historical as-filed universe panel; no historical return is reported.',
                'Original filings supplied through Massive, independent calculation not independent vendor.',
                'Individual Swedish broker instrument availability is not certified.',
                'Paper opening execution remains unverified until an actual future opening observation.'])
    except Exception as e:
        report.update(status='DATA_BLOCKED',generated_at=datetime.now(timezone.utc).isoformat(),paper_start_permit=False,
            errors=[str(e) if isinstance(e,DataUnavailable) else type(e).__name__])
    report['source_files']={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ('quality_sources.py','quality_fundamentals.py','quality_strategy.py','quality_audit.py','collect_quality.py','docs/QUALITY_EARNINGS_PROTOCOL_20261031.md')}
    atomic_json(out/'quality.json',report);print('FINAL',json.dumps({k:report.get(k) for k in ('status','universe_count','coverage','qualified_count','paper_start_permit','errors')}),flush=True)
    return report


def math_close(a,b):
    import math
    return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cache','manifest','fundamentals','output'):p.add_argument('--'+name,required=True)
    collect(p.parse_args())
