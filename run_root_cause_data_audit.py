#!/usr/bin/env python3
"""Reproduce existing models, audit data and export evidence; never select a new model."""
import argparse
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import pandas as pd
import backtest_momentum_v3 as engine
import run_v4_ablation_and_simple_candidate as existing

OUT = Path('Momentum_data_audit')

def write(name, value):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False, default=str)+'\n')

def safe_status(exc):
    response = getattr(exc, 'response', None)
    return {'error_type': type(exc).__name__, 'http_status': getattr(response, 'status_code', None)}

def pages(client, path, params):
    rows=[]
    while True:
        data=client._get(path, params)
        rows.extend(data.get('results', []) or [])
        if not data.get('next_url'):
            return rows
        parsed=urlparse(data['next_url'])
        path=parsed.path
        params={k:v[-1] for k,v in parse_qs(parsed.query).items() if k.lower()!='apikey'}

def exclusion_audit(cache, universes, client, end):
    days=sorted(cache)
    tickers=sorted({t for names in universes.values() for t in names})
    events=pages(client,'/stocks/v1/splits',{'execution_date.gte':days[0], 'execution_date.lte':end, 'limit':5000, 'sort':'execution_date.asc'})
    by_ticker={}
    for event in events:
        by_ticker.setdefault(event.get('ticker',''),[]).append(event)
    bad=engine.find_unverified_split_basis_tickers(cache,days,tickers,by_ticker)
    first={t:min(x[:10] for x in observations) for t,observations in bad.items()}
    records=[]
    for signal,names in sorted(universes.items()):
        affected=[t for t in names if t in first and first[t]>signal]
        records.append({'SignalDate':signal,'FutureOnlyExclusions':len(affected),'Tickers':','.join(sorted(affected))})
    pd.DataFrame(records).to_csv(OUT/'future_information_exclusions.csv',index=False)
    write('exclusion_events.json',{'first_suspicious_date':first,'events':bad,'split_event_count':len(events), 'split_events':events})
    return first,by_ticker

def linked_positions(run, cache):
    results=run['results'].copy()
    positions=run['positions'].copy()
    prefix=(1+results.NetReturn_pct/100).cumprod().shift(1,fill_value=1)
    prefix_map=dict(zip(results.SignalDate,prefix))
    positions['LinkedContribution_pp']=positions.apply(lambda p:p.GrossReturn_pct/p.TopN*prefix_map[p.SignalDate],axis=1)
    peak_rows=[]
    days=sorted(cache)
    for p in positions.itertuples():
        observations=[]
        for day in days:
            if p.EntryDate<=day<p.ExitDate:
                close,action=engine.position_close_on_day(cache,p.Ticker,day,p.EntryDate)
                if close is not None:
                    ticker,ratio,_=engine.valuation_identity(p.Ticker,day,p.EntryDate)
                    row=engine.get_from_map(cache[day],ticker)
                    cash=float(action.get('cash_per_share',0)) if action else 0.0
                    observations.append((day,float(row.get('high',row['close']))*ratio+cash,float(close)))
        high=max([float(p.EntryPrice_USD),float(p.ExitPrice_USD)]+[x[1] for x in observations])
        close=max([float(p.EntryPrice_USD),float(p.ExitPrice_USD)]+[x[2] for x in observations])
        peak_rows.append({'MaxIntradayReturn_pct':100*(high/p.EntryPrice_USD-1),'MaxCloseOrExitReturn_pct':100*(close/p.EntryPrice_USD-1),'ObservedSessions':len(observations)})
    positions=pd.concat([positions.reset_index(drop=True),pd.DataFrame(peak_rows)],axis=1)
    costs=sum(-0.30*prefix_map[r.SignalDate] for r in results.itertuples() if r.RiskRegime=='RISK_ON')
    residual=float(positions.LinkedContribution_pp.sum()+costs-run['metrics']['TotalReturn_pct'])
    if abs(residual)>1e-7:
        raise AssertionError('Linked attribution does not reconcile')
    return positions,{'LinkedCostContribution_pp':costs,'Residual_pp':residual,
        'IntradayAtLeast50':int((positions.MaxIntradayReturn_pct>=50).sum()),'IntradayAtLeast100':int((positions.MaxIntradayReturn_pct>=100).sum()),
        'CloseOrExitAtLeast50':int((positions.MaxCloseOrExitReturn_pct>=50).sum()),'CloseOrExitAtLeast100':int((positions.MaxCloseOrExitReturn_pct>=100).sum()),
        'definition':'Monthly lots. Daily high from entry open through the session before exit open, plus actual exit price. Not continuous multi-month holding episodes.'}

def turnover(run):
    """Minimum drift-aware two-sided trading if overlapping lots are retained."""
    previous={}
    records=[]
    for row in run['results'].itertuples():
        group=run['positions'].loc[run['positions'].SignalDate==row.SignalDate]
        target={p.Ticker:1/p.TopN for p in group.itertuples()}
        keys=set(previous)|set(target)
        buy=sum(max(0,target.get(t,0)-previous.get(t,0)) for t in keys)
        sell=sum(max(0,previous.get(t,0)-target.get(t,0)) for t in keys)
        stop_proceeds=sum((1+p.GrossReturn_pct/100)/p.TopN for p in group.itertuples() if p.ExitReason=='STOP_LOSS')
        gross_growth=1+row.GrossReturn_pct/100
        previous={p.Ticker:(1+p.GrossReturn_pct/100)/p.TopN/gross_growth for p in group.itertuples() if p.ExitReason!='STOP_LOSS'}
        records.append({'SignalDate':row.SignalDate,'RebalanceBuy_pct':100*buy,'RebalanceSell_pct':100*sell,'StopSale_pct_of_period_start':100*stop_proceeds})
    terminal=100*sum(previous.values())
    return records,{'MinimumRebalanceTwoSidedSum_pct':sum(r['RebalanceBuy_pct']+r['RebalanceSell_pct'] for r in records)+terminal,
       'StopSaleSum_pct_of_period_start':sum(r['StopSale_pct_of_period_start'] for r in records),
       'TerminalLiquidation_pct':terminal,'FixedCostModelRoundTripSum_pct':0.30*sum(run['results'].RiskRegime=='RISK_ON'),
       'definition':'Diagnostic minimum turnover, pre-cost drift weights, cash excluded. Stops measured against period-start capital. Not broker executions and not a turnover-adjusted performance backtest.'}

def historical_details(client, positions, reference_cache):
    details=[]
    for p in positions.itertuples():
        key=(p.Ticker,p.EntryDate)
        if key not in reference_cache:
            try:
                data=client._get('/v3/reference/tickers/'+p.Ticker,{'date':p.EntryDate}).get('results',{})
                reference_cache[key]={'Ticker':p.Ticker,'ReferenceDate':p.EntryDate,'SIC':data.get('sic_code'), 'Industry':data.get('sic_description') or 'UNKNOWN','CIK':data.get('cik'), 'Name':data.get('name'),'status':'OK'}
            except Exception as exc:
                reference_cache[key]={'Ticker':p.Ticker,'ReferenceDate':p.EntryDate,'SIC':None,'Industry':'UNKNOWN','status':'UNAVAILABLE',**safe_status(exc)}
        details.append(reference_cache[key])
    return pd.concat([positions.reset_index(drop=True),pd.DataFrame(details).drop(columns='Ticker')],axis=1)

def price_checks(client, positions, model):
    worst=positions.nsmallest(10,'GrossReturn_pct')
    best=positions.nlargest(5,'GrossReturn_pct')
    selected=pd.concat([worst,best]).drop_duplicates(['SignalDate','Ticker'])
    checks=[]
    for p in selected.itertuples():
        try:
            data=client._get(f'/v2/aggs/ticker/{p.Ticker}/range/1/day/{p.SignalDate}/{p.ExitDate}',{'adjusted':'true','sort':'asc','limit':50000})
            bars={datetime.fromtimestamp(r['t']/1000,timezone.utc).date().isoformat():r for r in data.get('results',[])}
            raw=client._get(f'/v2/aggs/ticker/{p.Ticker}/range/1/day/{p.SignalDate}/{p.SignalDate}',{'adjusted':'false','sort':'asc','limit':50000}).get('results',[])
            entry=bars.get(p.EntryDate,{}).get('o')
            exit=bars.get(p.ExitDate,{}).get('o')
            check={'Model':model,'Ticker':p.Ticker,'SignalDate':p.SignalDate,'EntryDate':p.EntryDate,'ExitDate':p.ExitDate,
                'StoredEntry':p.EntryPrice_USD,'AggregateEntry':entry,'StoredExit':p.ExitPrice_USD,'AggregateExit':exit,
                'CorporateAction':str(p.CorporateAction),'RawSignalClose':raw[0]['c'] if raw else None,
                'StoredSignalClose':p.SignalPrice_USD,'GrossReturn_pct':p.GrossReturn_pct,
                'EntryRelativeError':abs(entry/p.EntryPrice_USD-1) if entry else None,
                'ExitRelativeError':abs(exit/p.ExitPrice_USD-1) if exit else None,
                'source':'Separate per-ticker aggregate endpoint, same provider, not independent provider'}
            checks.append(check)
            write(f'{model}_{p.Ticker}_{p.SignalDate}_price_evidence.json',{'check':check,'adjusted_bars':data.get('results',[]),'unadjusted_signal_bars':raw})
        except Exception as exc:
            checks.append({'Model':model,'Ticker':p.Ticker,'SignalDate':p.SignalDate,**safe_status(exc)})
    return checks

def dividends(client,positions,cache,model):
    evidence=[]
    counts={}
    for ticker in sorted(set(positions.Ticker)|{'SPY'}):
        try:
            rows=pages(client,'/stocks/v1/dividends',{'ticker':ticker,'ex_dividend_date.gte':str(positions.EntryDate.min()),'ex_dividend_date.lte':str(positions.ExitDate.max()),'limit':5000,'sort':'ex_dividend_date.asc'})
            counts[ticker]={'records':len(rows),'status':'OK'}
            for row in rows:
                evidence.append({'ticker':ticker,**row})
        except Exception as exc:
            counts[ticker]={'status':'UNAVAILABLE',**safe_status(exc)}
    write(model+'_dividend_evidence.json',{'status':counts,'records':evidence,'purpose':'Verify omitted distributions. No unverified GICS mapping or inferred dividend amounts.'})
    return counts

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--start',default='2023-02-01')
    parser.add_argument('--end',default='2026-10-03')
    parser.add_argument('--verification-only',action='store_true')
    args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    os.environ.setdefault('POLYGON_MAX_RETRIES','5')
    os.environ.setdefault('POLYGON_RATE_LIMIT_WAIT_SECONDS','15')
    client=engine.PolygonClient(os.environ['POLYGON_API_KEY'])
    probes=[]
    for day in ['2020-08-03','2021-09-01','2021-11-08']:
        try:
            values=client.fetch_grouped_stocks(day)
            probes.append({'date':day,'rows':len(values),'status':'OK'})
        except Exception as exc:
            probes.append({'date':day,'status':'UNAVAILABLE',**safe_status(exc)})
    write('historical_access_probes.json',probes)
    flags={'m12':True,'m6':True,'vol':True,'extension':True}
    specs=[('v4',existing.v4_builder(flags),10.0),('simple',existing.simple_builder,None)]
    runs={}
    verification={}
    for name,builder,stop in specs:
        logging.warning('AUDIT reproduce %s',name)
        try:
            run=existing.run_one(name,builder,args.start,args.end,stop,False)
        except Exception as exc:
            if not args.verification_only:
                raise
            reason=str(exc) if isinstance(exc,RuntimeError) and str(exc).startswith(('No executable price','Only ','No executable rebalance')) else None
            verification[name]={'status':'BLOCKED_WITHOUT_GUESSING',**safe_status(exc),'execution_blockers':reason}
            write('corrected_engine_verification.json',verification)
            continue
        runs[name]=run
        run['results'].to_csv(OUT/(name+'_results.csv'),index=False)
        run['positions'].to_csv(OUT/(name+'_positions.csv'),index=False)
        write(name+'_metrics.json',{'metrics':run['metrics'],'out_of_sample_metrics':run['out_of_sample_metrics']})
        verification[name]={'status':'COMPLETE','metrics':run['metrics'],'remaining_limits':['gap screen not a proof of data corruption','dividends omitted','historical dollar-volume basis still needs reconciliation']}
    if args.verification_only:
        write('corrected_engine_verification.json',verification)
        print('CORRECTED_ENGINE_VERIFICATION '+json.dumps(verification,allow_nan=False))
        return
    cache,basis=engine.load_backtest_cache(engine.CACHE_FILE)
    universes=engine.load_point_in_time_universe_cache(engine.UNIVERSE_CACHE_FILE)
    first,split_events=exclusion_audit(cache,universes,client,args.end)
    write('audit_metadata.json',{'start':args.start,'end':args.end,'price_basis_date':basis,'original_models_unchanged':True,
      'validity':'ORIGINAL_RESULTS_INVALID_FOR_CAUSAL_MODEL_CONCLUSIONS: full-period exclusion uses future information; absolute price floors use latest split-adjusted basis',
      'source':'Massive/Polygon grouped and per-ticker bars; historical ticker details supply SIC industries, not GICS sectors'})
    references={}
    summary={}
    for name,run in runs.items():
        logging.warning('AUDIT detailed evidence %s',name)
        enriched,linked=linked_positions(run,cache)
        enriched=historical_details(client,enriched,references)
        enriched.to_csv(OUT/(name+'_enriched_positions.csv'),index=False)
        enriched.groupby(['SIC','Industry'],dropna=False).agg(Positions=('Ticker','size'),LinkedContribution_pp=('LinkedContribution_pp','sum')).sort_values('LinkedContribution_pp').to_csv(OUT/(name+'_sic_industry_contributions.csv'))
        enriched.groupby('Ticker').agg(Positions=('Ticker','size'),LinkedContribution_pp=('LinkedContribution_pp','sum')).sort_values('LinkedContribution_pp').to_csv(OUT/(name+'_ticker_contributions.csv'))
        records,turn=turnover(run)
        pd.DataFrame(records).to_csv(OUT/(name+'_minimum_turnover.csv'),index=False)
        checks=price_checks(client,enriched,name)
        pd.DataFrame(checks).to_csv(OUT/(name+'_price_checks.csv'),index=False)
        summary[name]={'linked':linked,'turnover':turn,'historical_industry_coverage_pct':float(enriched.SIC.notna().mean()*100),
            'stop_count':int((enriched.ExitReason=='STOP_LOSS').sum()),'positions':len(enriched),'price_checks':len(checks)}
    write('historical_reference_evidence.json',list(references.values()))
    # This diagnostic removes future-only exclusions at each formation date.
    # It is the same two strategies, not a candidate search; unresolved execution aborts honestly.
    old_find,old_choose=engine.find_unverified_split_basis_tickers,engine.choose_top
    engine.find_unverified_split_basis_tickers=lambda *_a,**_k:{}
    def causal_choose(client,cache,tickers,asof,*a,**kw):
        return old_choose(client,cache,[t for t in tickers if t not in first or first[t]>asof],asof,*a,**kw)
    engine.choose_top=causal_choose
    for name,builder,stop in specs:
        try:
            logging.warning('AUDIT temporal-exclusion diagnostic %s',name)
            run=existing.run_one(name+'_temporal_exclusions',builder,args.start,args.end,stop,False)
            run['results'].to_csv(OUT/(name+'_temporal_results.csv'),index=False)
            run['positions'].to_csv(OUT/(name+'_temporal_positions.csv'),index=False)
            summary[name]['temporal_diagnostic']={'status':'COMPLETE','metrics':run['metrics'], 'remaining_limitations':['future split-adjusted absolute price floor','SIC is not GICS','cash-merger settlement split basis not independently reconciled']}
        except Exception as exc:
            summary[name]['temporal_diagnostic']={'status':'INCOMPLETE',**safe_status(exc)}
    engine.find_unverified_split_basis_tickers,engine.choose_top=old_find,old_choose
    # Dividend reference requests are optional evidence, never cause guessed performance.
    for name,run in runs.items():
        summary[name]['dividend_reference_status']=dividends(client,run['positions'],cache,name)
    write('audit_summary.json',summary)
    print('AUDIT_COMPLETED '+json.dumps({k:{x:y for x,y in v.items() if x!='dividend_reference_status'} for k,v in summary.items()},allow_nan=False))

if __name__=='__main__':
    main()
