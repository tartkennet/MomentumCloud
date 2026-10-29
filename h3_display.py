"""Read-only SEK presentation of accepted H3 accounts. Never computes signals.

Scaled virtual units replicate the USD account, not a new whole-share strategy.
The paper journal remains authoritative; live marks never enter its NAV/history.
"""
import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT=Path(__file__).resolve().parent
BRANCH='h3-observed-snapshots'
DISPLAY_BRANCH='h3-sek-valuations'
FP='e89ab72e0354d1983a4055ec330cc8b5234cf73615cdf1805bb0bb2517c09921'
NY=ZoneInfo('America/New_York')


def read(path,default=None):
    p=Path(path)
    if not p.exists():return copy.deepcopy(default)
    if p.suffix=='.gz':
        with gzip.open(p,'rt') as f:return json.load(f)
    return json.loads(p.read_text())


def write(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def export_account(record,cache,previous=None):
    record=Path(record);snap=read(record/'H3_snapshot.json',{})
    if snap.get('source_fingerprint')!=FP or snap.get('operations',{}).get('errors'):raise ValueError('No independently accepted H3 export')
    cp=read(record/'Momentum_core_paper_checkpoint.json')
    result={'schema_version':1,'source_fingerprint':FP,'as_of':snap['as_of'],'source_run':snap['operations']['workflow_run'],
            'checkpoint_sha256':digest(cp),'account':cp['strategy'] if cp else None,'benchmark':cp['benchmark'] if cp else None,
            'holdings':snap['holdings'],'latest_decision':snap['latest_decision'],'splits':(previous or {}).get('splits',[]),
            'live_approved':False,'broker_orders_enabled':False}
    if cp:
        if cp['source_fingerprint']!=FP:raise ValueError('Wrong checkpoint identity')
        old=(previous or {}).get('account')
        if old:
            for field in ('equity','trades','targets'):
                if result['account'][field][:len(old[field])]!=old[field]:raise ValueError('Changed accepted account prefix')
        inputs=read(record/'Momentum_core_inputs.json',{})
        existing={digest(e):e for e in result['splits']}
        for label in inputs:
            if label.startswith('splits/'):
                _,start,end=label.split('/')
                for event in read(Path(cache)/f'splits-{start}-{end}-v1.json.gz',[]):
                    if cp['strategy']['equity'][0]['date']<=event['execution_date']<=cp['strategy']['last_date']:
                        existing[digest(event)]=event
        result['splits']=list(existing.values())
    return result


def query(key,path,params=None):
    """No retries and no credential-bearing exception text or response headers."""
    try:
        r=requests.get('https://api.polygon.io'+path,params=dict(params or {},apiKey=key),timeout=(3,8))
        if r.status_code!=200:return {'error':'HTTP_'+str(r.status_code)}
        return r.json()
    except Exception as exc:return {'error':type(exc).__name__}


def ecb_rates():
    """ECB reference fixing, SEK per USD, never described as a tradeable quote."""
    response=requests.get('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml',timeout=(3,10))
    response.raise_for_status();root=ET.fromstring(response.content);result={}
    for day in root.iter():
        if 'time' not in day.attrib:continue
        values={e.attrib.get('currency'):float(e.attrib['rate']) for e in day if 'rate' in e.attrib}
        if 'USD' in values and 'SEK' in values:result[day.attrib['time']]=values['SEK']/values['USD']
    if not result:raise ValueError('No USD/SEK fixing')
    return result


def rate_on(rates,day,strict=False):
    candidates=[d for d in rates if d<day or (not strict and d==day)]
    if not candidates:return None
    key=max(candidates);age=(datetime.fromisoformat(day)-datetime.fromisoformat(key)).days
    if age>7:return None
    return {'date':key,'usdsek':rates[key],'source':'ECB reference fixing','stale_days':age}


def market_quotes(key,tickers,now,as_of=None):
    today=now.astimezone(NY).date();end=(today-timedelta(days=1)).isoformat();start=(today-timedelta(days=9)).isoformat()
    symbols=sorted(set(tickers))
    params={'ticker':symbols[0],'limit':1} if len(symbols)==1 else {'ticker.any_of':','.join(symbols),'limit':250}
    probe=query(key,'/v3/snapshot',params) if key else {'error':'KEY_UNAVAILABLE'}
    unified={r['ticker']:r for r in probe.get('results',[]) if r.get('ticker')}
    frames={t:r.get('timeframe') for t,r in unified.items()}
    cap={'checked_at':now.isoformat(),'snapshot_status':probe.get('error',probe.get('status','UNKNOWN')),
         'realtime_verified':any(v=='REAL-TIME' for v in frames.values()),'timeframes':frames,
         'selected_mode':'CLOSE','provider_latency':'VERIFIED_TIMEFRAME' if any(frames.values()) else 'UNVERIFIED',
         'display_refresh_minutes':15,
         'subscription_changed':False}
    # Only explicit per-ticker timeframe metadata establishes the entitlement.
    def one(t):
        row=unified.get(t,{})
        if row:
            trade=row.get('last_trade') or {};price=row.get('session',{}).get('price')
            stamp=trade.get('sip_timestamp') or trade.get('last_updated') or row.get('session',{}).get('last_updated') or row.get('last_updated')
            if price and stamp:
                at=datetime.fromtimestamp(stamp/1e9,timezone.utc)
                if at<=now and (now-at).total_seconds()<86400:
                    return t,{'usd':price,'at':at.isoformat(),'session':at.astimezone(NY).date().isoformat(),
                              'mode':'REALTIME' if row.get('timeframe')=='REAL-TIME' else 'DELAYED',
                              'provider_timeframe':row.get('timeframe','UNVERIFIED'),
                              'delay_basis':'15_MINUTE_SAMPLED_DISPLAY_PROVIDER_LATENCY_NOT_ASSUMED',
                              'source':'Massive unified snapshot'}
        p=query(key,f'/v2/aggs/ticker/{t}/range/1/day/{start}/{end}',{'adjusted':'false','sort':'desc','limit':8}) if key else {}
        rows=p.get('results') or []
        if not rows:return t,{'error':p.get('error','CLOSE_UNAVAILABLE'),'mode':'MISSING'}
        row=max(rows,key=lambda v:v['t']);day=datetime.fromtimestamp(row['t']/1000,timezone.utc).astimezone(NY).date().isoformat()
        # Daily aggregate identifies the session; 16:00 is not claimed as a
        # tick timestamp (early closes exist). Display the session date only.
        return t,{'usd':row['c'],'at':None,'session':day,'mode':'CLOSE','source':'Massive raw daily close'}
    with ThreadPoolExecutor(max_workers=4) as pool:quotes=dict(pool.map(one,symbols))
    cap['selected_mode']='INTRADAY' if any(q.get('mode') in ('REALTIME','DELAYED') for q in quotes.values()) else 'CLOSE'
    if as_of:
        future=[t for t,m in quotes.items() if m.get('session','')>as_of]
        if future:
            through=max(quotes[t]['session'] for t in future);unsafe=set();unverified=False
            for kind,col in [('splits','execution_date'),('dividends','ex_dividend_date')]:
                p=query(key,'/stocks/v1/'+kind,{col+'.gt':as_of,col+'.lte':through,'limit':5000})
                if p.get('error') or p.get('next_url'):unverified=True
                unsafe.update(e['ticker'] for e in p.get('results',[]) if e.get('ticker') in future)
            for t in future:
                if unverified or t in unsafe:quotes[t]={'mode':'MISSING','error':'UNBOOKED_CORPORATE_EVENT_OR_UNVERIFIED_EVENT_INPUT'}
            cap['corporate_event_guard']={'through':through,'blocked_tickers':future if unverified else sorted(unsafe)}
    return cap,quotes


def basis_and_trades(account,splits,rates,scale):
    basis={};trades=[];events={}
    for e in splits:events.setdefault(e['execution_date'],[]).append(e)
    source=account['trades'];dates=sorted(set([t['date'] for t in source]+list(events)))
    for day in dates:
        for e in events.get(day,[]):
            if e['ticker'] in basis:basis[e['ticker']]['quantity']*=e['split_to']/e['split_from']
        for index,t in enumerate(source):
            if t['date']!=day:continue
            fx=rate_on(rates,day,strict=True);row=copy.deepcopy(t);q=t['quantity'];symbol=t['ticker'];side=t['side']
            if side=='BUY':
                b=basis.setdefault(symbol,{'quantity':0.,'usd':0.,'sek':0.})
                cost=q*t['price']+t['fee'];b['quantity']+=q;b['usd']+=cost
                b['sek']=b['sek']+cost*fx['usdsek'] if b['sek'] is not None and fx else None
            elif side=='SELL' and symbol in basis:
                b=basis[symbol];fraction=q/b['quantity']
                b.update(quantity=b['quantity']-q,usd=b['usd']*(1-fraction),sek=b['sek']*(1-fraction) if b['sek'] is not None else None)
                if b['quantity']<1e-8:del basis[symbol]
            elif side not in ('BUY','SELL','BUY_CANCELLED_NO_OPEN'):
                # Never guess acquisition basis after a distribution/merger.
                basis.pop(symbol,None)
            row.update(id=hashlib.sha256((str(index)+json.dumps(t,sort_keys=True)).encode()).hexdigest()[:20],
                       quantity=q*scale,fee_usd=t['fee']*scale,fee_sek=t['fee']*scale*fx['usdsek'] if fx else None,
                       notional_sek=q*(t.get('price') or 0)*scale*fx['usdsek'] if fx else None,fx=fx,
                       source_quantity=q,source_account='Frozen H3 USD paper',
                       at=datetime.fromisoformat(day).replace(hour=9,minute=30,tzinfo=NY).astimezone(timezone.utc).isoformat() if side in ('BUY','SELL') else None,
                       time_basis='SIMULATED_REGULAR_OPEN' if side in ('BUY','SELL') else 'EVENT_DATE')
            trades.append(row)
    return basis,trades


def build(account,previous,rates,quotes,capability,now):
    if account.get('source_fingerprint')!=FP:raise ValueError('Wrong accepted H3 source')
    a=account.get('account');b=account.get('benchmark');errors=[]
    anchor=copy.deepcopy((previous or {}).get('anchor'))
    result={'schema_version':1,'source_fingerprint':FP,'generated_at':now.isoformat(),'source_run':account['source_run'],
            'source_as_of':account['as_of'],'source_checkpoint_sha256':account['checkpoint_sha256'],
            'status':'WAITING','start_capital_sek':100000,'anchor':anchor,'fx_history':rates,
            'fx':rate_on(rates,now.date().isoformat()),'capability':capability,'quotes':quotes,
            'metrics':None,'positions':[],'trades':[],'curve':[],'sessions':len(a['equity']) if a else 0,
            'latest_decision':account['latest_decision'],'pending_intentions':a.get('pending') if a else None,
            'cost_bps':15,'errors':errors,'live_approved':False,'broker_orders_enabled':False,
            'method':'PROPORTIONAL_VIRTUAL_UNITS','valuation_is_validation':False}
    if not a:return result
    first=a['equity'][0];fx0=rate_on(rates,first['date'])
    if not anchor and fx0:
        anchor={'paper_start':first['date'],'fx':fx0,'scale':100000/(first['nav']*fx0['usdsek']),
                'recorded_at':now.isoformat(),'basis':'100000 SEK proportional presentation of accepted USD account'}
    if not anchor:result.update(status='FX_MISSING');errors.append('Startens USD/SEK-referenskurs saknas. Ingen SEK-avkastning kan beräknas.');return result
    if anchor['paper_start']!=first['date']:raise ValueError('Display anchor changed cohort')
    if not math.isclose(anchor['scale']*first['nav']*anchor['fx']['usdsek'],100000.,rel_tol=1e-12):raise ValueError('Display start capital changed')
    result['anchor']=anchor;scale=anchor['scale'];fx=result['fx'];basis,trades=basis_and_trades(a,account.get('splits',[]),rates,scale)
    result['trades']=trades
    valid=True;stock=0.
    closes={r['ticker']:r for r in account['holdings']}
    for t,q in a['shares'].items():
        mark=quotes.get(t,{});price=mark.get('usd')
        # A live valuation may not use a pre-split price for post-split shares.
        if price is None or mark.get('session','')<a['last_date']:
            close=closes.get(t,{}).get('mark_usd');price=close
            mark={'usd':close,'session':a['last_date'],'mode':'CLOSE','at':None,'source':'Accepted H3 close'}
        position_basis=basis.get(t)
        if position_basis and not math.isclose(position_basis['quantity'],q,rel_tol=1e-8,abs_tol=1e-7):position_basis=None
        value=q*scale*price if price is not None else None
        if value is None:valid=False
        else:stock+=value
        cost=position_basis['sek']*scale if position_basis and position_basis['sek'] is not None else None
        current=value*fx['usdsek'] if value is not None and fx else None
        result['positions'].append({'ticker':t,'quantity':q*scale,'source_quantity':q,'virtual_fractional':True,
            'average_cost_usd':position_basis['usd']/q if position_basis else None,'cost_sek':cost,
            'mark':mark,'value_sek':current,'pnl_sek':current-cost if current is not None and cost is not None else None,
            'return_pct':100*(current/cost-1) if current is not None and cost else None})
    benchmark_stock=0.
    for t,q in b['shares'].items():
        m=quotes.get(t,{});p=m.get('usd') if m.get('session','')>=a['last_date'] else None
        if p is None:
            # Benchmark holds SPY only. Its closing equity supplies the
            # accepted aggregate mark without inventing an individual price.
            benchmark_stock=b['equity'][-1]['stock_value']*scale;break
        benchmark_stock+=q*p*scale
    claims=sum(r['amount'] for r in a['receivables'])*scale
    for left,right in zip(a['equity'],b['equity']):
        rate=rate_on(rates,left['date'])
        result['curve'].append({'date':left['date'],'nav_sek':left['nav']*scale*rate['usdsek'] if rate else None,
                                'spy_sek':right['nav']*scale*rate['usdsek'] if rate else None,
                                'fx':rate,'kind':'ACCEPTED_PAPER_CLOSE_IN_SEK'})
    if not fx:errors.append('Aktuell verifierad USD/SEK-referenskurs saknas. SEK-värderingen är spärrad.')
    if not valid:errors.append('Kurs saknas för ett eller flera innehav.')
    if fx and valid:
        nav=(a['cash']*scale+stock+claims)*fx['usdsek']
        spy=(b['cash']*scale+benchmark_stock+sum(r['amount'] for r in b['receivables'])*scale)*fx['usdsek']
        pnl=nav-100000;spy_return=100*(spy/100000-1)
        result['metrics']={'nav_sek':nav,'pnl_sek':pnl,'return_pct':pnl/1000,'spy_nav_sek':spy,
                           'spy_return_pct':spy_return,'edge_pct':pnl/1000-spy_return,'cash_sek':a['cash']*scale*fx['usdsek'],
                           'receivables_sek':claims*fx['usdsek'],'fees_usd':a['fees']*scale}
    for p in result['positions']:p['weight_pct']=100*p['value_sek']/result['metrics']['nav_sek'] if p['value_sek'] is not None and result['metrics'] else None
    result['status']='ACTIVE' if not errors else 'DATA_MISSING'
    return result


def git(*args,cwd=ROOT):return subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True,check=True,timeout=45).stdout.strip()


def refresh():
    git('fetch','--no-tags','origin',BRANCH)
    account=json.loads(git('show','FETCH_HEAD:public/data/h3-account.json'))
    exists=git('ls-remote','--heads','origin','refs/heads/'+DISPLAY_BRANCH)
    if exists:
        git('fetch','--no-tags','origin',DISPLAY_BRANCH);head=git('rev-parse','FETCH_HEAD')
    else:head=git('rev-parse','HEAD')
    with tempfile.TemporaryDirectory(prefix='h3-marks-') as temp:
        work=Path(temp)/'work';git('worktree','add','--detach',str(work),head)
        try:
            if not account:raise ValueError('Accepted account export is not published yet')
            file=work/'public/data/h3-display.json';old=read(file,{})
            rates=dict(old.get('fx_history',{}));now=datetime.now(timezone.utc);fx_error=None
            try:
                # Preserve every previously observed fixing, including revisions.
                for day,rate in ecb_rates().items():
                    if day<=now.date().isoformat() and math.isfinite(rate) and rate>0:rates.setdefault(day,rate)
            except Exception as exc:fx_error=type(exc).__name__
            symbols=list((account.get('account') or {}).get('shares',{}))+['SPY']
            cap,quotes=market_quotes(os.getenv('POLYGON_API_KEY'),symbols,now,account['as_of'])
            data=build(account,old,rates,quotes,cap,now)
            if fx_error:data['errors'].append('ECB-uppdatering misslyckades: '+fx_error+'. Senast verifierade kurs visas med datum om den är tillräckligt färsk.')
            data['refresh_run']=os.getenv('GITHUB_RUN_ID');write(file,data)
            extra=[]
            if not exists:
                (work/'vercel.json').write_text((ROOT/'vercel.json').read_text());extra=['vercel.json']
            git('add','public/data/h3-display.json',*extra,cwd=work)
            git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com',
                'commit','-m','Refresh separate H3 SEK valuation '+str(os.getenv('GITHUB_RUN_ID','manual')),cwd=work)
            git('push','origin',f'HEAD:refs/heads/{DISPLAY_BRANCH}',cwd=work)
            print(json.dumps({'status':data['status'],'sessions':data['sessions'],'capability':cap,'fx':data['fx'],'errors':data['errors']}))
        finally:git('worktree','remove','--force',str(work))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['refresh']);p.parse_args();refresh()
