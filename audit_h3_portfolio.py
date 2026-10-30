"""Read-only first-portfolio review; never writes a paper account or runs a replay."""
import argparse, bisect, calendar, copy, csv, gzip, hashlib, json, math, os, statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import requests
from momentum_core import CONFIG
from momentum_core_data import CoreData
from run_core_risk_research import DailyEvents
from research_core_actions import supplement
from research_core_ledger import CASH_COMPLETIONS, STOCK_COMPLETIONS
from audit_core_normalized import population, expected_weights, closes_at, near
from audit_portfolio_risk import expected_risk
from run_portfolio_forward import fingerprint, development_identity

FP='e89ab72e0354d1983a4055ec330cc8b5234cf73615cdf1805bb0bb2517c09921'

def read(p):
    p=Path(p)
    if p.suffix=='.gz':
        with gzip.open(p,'rt') as f:return json.load(f)
    return json.loads(p.read_text())

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def query(path,params=None):
    try:
        r=requests.get('https://api.polygon.io'+path,params=dict(params or {},apiKey=os.environ['POLYGON_API_KEY']),timeout=(3,8))
        if r.status_code!=200:return {'error':'HTTP_'+str(r.status_code)}
        return r.json()
    except Exception as e:return {'error':type(e).__name__}

def months_before(day,months):
    d=date.fromisoformat(day);m=d.year*12+d.month-1-months;y,m=divmod(m,12);m+=1
    return date(y,m,min(d.day,calendar.monthrange(y,m)[1])).isoformat()

def period_return(prices,events,dividends,ticker,end,months):
    """Calendar-month endpoints, split-neutral price and reinvested cash dividends."""
    dates=sorted(d for d,p in prices.items() if p is not None and d<=end)
    target=months_before(end,months);i=bisect.bisect_right(dates,target)-1
    if i<0 or not dates or dates[-1]!=end:return {'status':'MISSING'}
    start=dates[i];p0=prices[start];q=1.;wealth=p0
    relevant=[e for e in events if e.get('ticker')==ticker and start<e['execution_date']<=end]
    payouts=[e for e in dividends if e.get('ticker')==ticker and start<e['ex_dividend_date']<=end]
    for day in dates[i+1:]:
        for e in relevant:
            if e['execution_date']==day:q*=float(e['split_to'])/float(e['split_from'])
        for e in payouts:
            if e['ex_dividend_date']==day:
                if e.get('currency','').upper()!='USD' or e.get('cash_amount') is None:return {'status':'UNRESOLVED_DIVIDEND'}
                q+=q*float(e['cash_amount'])/prices[day]
        wealth=q*prices[day]
    split_factor=math.prod(float(e['split_to'])/float(e['split_from']) for e in relevant)
    return {'status':'PASS','start':start,'end':end,'start_raw_close':p0,'end_raw_close':prices[end],
            'price_return_pct':100*(split_factor*prices[end]/p0-1),'total_return_pct':100*(wealth/p0-1),
            'split_events':relevant,'dividend_count':len(payouts),'total_return_method':'USD_EX_DATE_CLOSE_REINVESTMENT_NO_TAX_OR_FEES'}

def unique(rows):
    return list({json.dumps(r,sort_keys=True):r for r in rows}.values())

def historical_evidence(root,current):
    root=Path(root);files=list(root.rglob('Momentum_core_targets.json'));evidence=[]
    # One complete, pre-existing 15bp display account; never re-run or optimize it.
    for p in files:
        dec=p.with_name('Momentum_core_decision.json')
        if not dec.exists():continue
        d=read(dec)
        if d.get('end')!='2026-10-28' or d.get('config',{}).get('one_way_cost')!=.0015:continue
        if 'assumed_5' not in str(p) or 'last_quote' not in str(p):continue
        signals=read(p);state=read(p.with_name('Momentum_core_state.json'))
        daily=state['equity'];peak=daily[0];worst=None
        for row in daily:
            if row['nav']>peak['nav']:peak=row
            dd=100*(row['nav']/peak['nav']-1)
            if worst is None or dd<worst['drawdown_pct']:worst={'peak':peak['date'],'trough':row['date'],'drawdown_pct':dd}
        groups={'biopharma':{'ERAS','SLS','CLYM','SYRE','RVMD'},'health_tools_diagnostics':{'TXG','TWST','CDNA'},'storage_semis_optics':{'SNDK','AXTI','MU','STX','LITE'}}
        snapshots=[]
        for s in signals:
            weights={r['ticker']:r['weight'] for r in s['targets']}
            snapshots.append({'date':s['date'],'risk_on':s['risk_on'],
                **{k:sum(weights.get(t,0) for t in names) for k,names in groups.items()},
                'current_names_present':[t for t in current if weights.get(t,0)>0]})
        evidence.append({'path':str(p.relative_to(root)),'metrics':d.get('metrics'),'max_drawdown':worst,
                         'historical_signals':snapshots,'note':'Only current names are grouped. This is not an exhaustive historical sector classification.'})
        break
    return {'archive_files':len(files),'display_accounts':evidence,
            'scope':'Read existing H3 states/targets only; no backtest, new parameter, or untouched OOS claim.'}

def run(record,cache,historical,output,live):
    record,cache=Path(record),Path(cache);tracked={p.name:digest(p) for p in record.glob('*') if p.is_file()}
    cp=read(record/'Momentum_core_paper_checkpoint.json');assert cp['source_fingerprint']==fingerprint()==FP
    signal=cp['strategy']['targets'][0];day=signal['date'];assert day=='2026-10-29'
    data=supplement(DailyEvents(CoreData(None,'2026-10-29',day,cache,offline=True)))
    data.source.cash_actions=dict(data.source.cash_actions,**copy.deepcopy(CASH_COMPLETIONS));data.cash_actions=copy.deepcopy(data.source.cash_actions)
    data.source.stock_actions=dict(data.source.stock_actions,**copy.deepcopy(STOCK_COMPLETIONS))
    ranked=population(data,day,CONFIG,formation=True);base=ranked[:15]
    assert len(ranked)==signal['eligible_count'];assert [r['ticker'] for r in base]==[r['ticker'] for r in signal['targets'] if r['ticker']!='SPY']
    weights=expected_weights(base,CONFIG)
    for r in base:r['weight']=weights[r['ticker']]
    independent,pvol_scale,pvol,svol=expected_risk(data,day,base,CONFIG)
    fraction=1/(1+pvol/svol);near(sum(r['weight'] for r in signal['targets']),1.,'budget')
    rows=[];tickers=[r['ticker'] for r in signal['targets']]
    for i,r in enumerate(signal['targets']):
        if r['ticker']=='SPY':near(r['weight'],1-fraction,'SPY weight')
        else:
            expected=ranked[i]
            for key in ('momentum_12_2','daily_volatility','raw_price','adv20_usd','formation_volatility','risk_normalized_score'):near(r[key],expected[key],key)
            near(r['weight'],independent[r['ticker']]*fraction,'stock weight');near(r['portfolio_vol63'],pvol,'basket vol');near(r['benchmark_vol63'],svol,'SPY vol')
        history=data.history(day,r['ticker'],253);closes=closes_at(data,day,r['ticker'],253)
        rows.append(dict(r,rank=i+1 if r['ticker']!='SPY' else None,
                         formation={'start_date':history[252][0],'end_date':history[21][0],
                         'start_split_adjusted_close':closes[252],'end_split_adjusted_close':closes[21],
                         'excluded_recent_start':history[20][0],'signal_close_date':day}))
    original=read(record/'Momentum_core_inputs.json');matched=0
    for label,h in data.source.used_inputs.items():
        if label in original:assert h==original[label],label;matched+=1
    assert matched>=254
    # Existing cache is read only; live additions are isolated in this report.
    events=unique([e for p in cache.glob('splits-*.json.gz') for e in read(p)])
    dividends=unique([e for p in cache.glob('dividends-*.json.gz') for e in read(p)])
    # Overlapping saved files may carry the same provider event with identical ID.
    def dedupe(items,kind):
        result={}
        for e in items:
            k=e.get('id') or (e.get('ticker'),e.get('execution_date') or e.get('ex_dividend_date'),e.get('cash_amount'),e.get('split_from'),e.get('split_to'))
            if k in result:assert result[k]==e,(kind,k)
            result[k]=e
        return list(result.values())
    events=dedupe(events,'split');dividends=dedupe(dividends,'dividend')
    latest='2026-10-30';live_data={};refs={};errors=[]
    if live:
        grouped=query('/v2/aggs/grouped/locale/us/market/stocks/'+latest,{'adjusted':'false','include_otc':'false'})
        live_data={r['T']:r for r in grouped.get('results',[]) if r.get('T') in tickers}
        if len(live_data)!=len(tickers):errors.append('LATEST_SESSION_QUOTES_INCOMPLETE')
        for kind,column in [('splits','execution_date'),('dividends','ex_dividend_date')]:
            extra=query('/stocks/v1/'+kind,{column+'.gte':day,column+'.lte':latest,'limit':5000})
            if extra.get('error') or extra.get('next_url'):raise ValueError('Corporate-action coverage incomplete: '+kind)
            if kind=='splits':events=dedupe(events+extra.get('results',[]),'split')
            else:dividends=dedupe(dividends+extra.get('results',[]),'dividend')
        def reference(t):return t,query('/v3/reference/tickers/'+t,{'date':day})
        with ThreadPoolExecutor(max_workers=4) as pool:refs=dict(pool.map(reference,tickers))
    for row in rows:
        t=row['ticker'];prices={stamp:bar[1] for stamp,bar in data.history(day,t,len(data.days)) if bar}
        if t in live_data:prices[latest]=live_data[t].get('c')
        row['returns_at_signal']={str(m):period_return(prices,events,dividends,t,day,m) for m in (1,3,6,12)}
        row['returns_latest']={str(m):period_return(prices,events,dividends,t,latest,m) for m in (1,3,6,12)} if t in live_data else None
        row['latest_raw_bar']=live_data.get(t);ref=refs.get(t,{}).get('results',{})
        row['reference']={k:ref.get(k) for k in ('name','sic_code','sic_description','description','homepage_url','cik','primary_exchange','type')}
        row['reference']['verified']=bool(ref.get('name'));row['reference']['as_of']=day
        row['reference']['endpoint']='https://api.polygon.io/v3/reference/tickers/'+t+'?date='+day
        # Report the reversal in the deliberately excluded recent month.
        h=data.history(day,t,253);row['excluded_month_return_pct']=100*(prices[day]/(closes_at(data,day,t,253)[21])-1)
    before=cp['strategy'];assert {p.name:digest(p) for p in record.glob('*') if p.is_file()}==tracked
    result={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),'signal_date':day,
            'latest_price_date':latest if live_data else day,'source_fingerprint':FP,'development_fingerprint':development_identity(),
            'audit':{'status':'PASS','independent_eligible_count':len(ranked),'saved_input_hashes_checked':matched,'record_files_unchanged':True,
                     'portfolio_vol63':pvol,'spy_vol63':svol,'momentum_fraction':fraction},
            'positions':rows,'next_ranked':[dict(r,rank=i+16) for i,r in enumerate(ranked[15:20])],
            'paper':{'as_of':before['last_date'],'sessions':len(before['equity']),'holdings':before['shares'],'cash_usd':before['cash'],
                     'trades':before['trades'],'pending':before['pending'],'checkpoint_sha256':digest(record/'Momentum_core_paper_checkpoint.json')},
            'historical':historical_evidence(historical,tickers),'errors':errors,
            'live_approved':False,'broker_orders_enabled':False}
    Path(output).write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({'audit':result['audit'],'errors':errors,'positions':len(rows),'historical_accounts':len(result['historical']['display_accounts'])}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',required=True);p.add_argument('--cache',required=True);p.add_argument('--historical',required=True);p.add_argument('--output',required=True);p.add_argument('--live',action='store_true');a=p.parse_args()
    run(a.record,a.cache,a.historical,a.output,a.live)
