"""Resumable original-file panels for a bounded historical reconstruction."""
import argparse,copy,gzip,hashlib,json,math,concurrent.futures
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import momentum_core as core
from momentum_core_data import atomic_json,read_json
from run_core_risk_research import make_data
from research_core_actions import supplement
from collect_quality import PriceProvider
from quality_sources import Provider,DataUnavailable,iso_date,save_original
from quality_strategy import division
from historical_quality_facts import available_at,parse_historical
from historical_quality_audit import audit_fundamental
from run_stocks10_research import fx_rows,prior_fx

START,END='2026-07-01','2026-10-28'

def data(cache,offline=False):
    import run_core_risk_research as adapter
    adapter.PolygonClient=lambda key:PriceProvider()
    return supplement(make_data(cache,END,offline))

def broad_universe(d,day):
    spy=core.adjusted_history(d,day,'SPY',253);rs=spy[0]/spy[126];rows=[];seen=set()
    for r in d.universe(day):
        if not core.eligible(r) or r['primary_exchange'] not in ('XNAS','XNYS') or not r.get('cik'):continue
        t=r['ticker'];history=d.history(day,t,253)
        if len(history)!=253 or any(not b for _,b in history):continue
        p=history[0][1][1];adv=sum(b[1]*b[2] for _,b in history[:20])/20
        if p<10 or adv<20_000_000:continue
        c=core.adjusted_history(d,day,t,253)
        if c[0]<=sum(c[:200])/200 or c[0]/c[126]<=rs:continue
        rows.append(dict(ticker=t,cik=str(r['cik']).zfill(10),name=r['name'],price_usd=p,adv20_usd=adv,relative_strength=(c[0]/c[126])/rs-1,return_6m=c[0]/c[126]-1,price_as_of=day))
    out=[]
    for r in sorted(rows,key=lambda r:(-r['adv20_usd'],r['ticker'])):
        if r['cik'] not in seen:out.append(r);seen.add(r['cik'])
    return out[:200]

def prepare(cache,out):
    d=data(cache);days=[x for x in d.sessions if START<=x<=END];signals=[];prev=False;month=''
    for day in days:
        prior=d.days[d.index[day]-1];spy=core.adjusted_history(d,prior,'SPY',200);on=spy[0]>sum(spy)/200
        if day[:7]!=month or (on and not prev):
            universe=broad_universe(d,prior);atomic_json(out/(day+'.universe.json'),dict(date=day,price_as_of=prior,rows=universe,risk_on=on));signals.append(day)
        prev=on;month=day[:7]
    atomic_json(out/'signals.json',signals);print(json.dumps(signals));return signals

def original(row,day,root):
    row=copy.deepcopy(row);p=Provider();decision=day+'T08:17:00+00:00';stamp=datetime.now(timezone.utc).isoformat()
    try:
        choices=[]
        for form in ('10-K','10-Q'):
            payload=p.get('/v1/reference/sec/filings',{'entities.company_data.cik':row['cik'],'type':form,'filing_date.lte':day.replace('-',''),'order':'desc','sort':'filing_date','limit':3})
            choices.extend(f for f in payload.get('results',[]) if available_at(f)<=datetime.fromisoformat(decision))
        if not choices:raise DataUnavailable('NO_AS_OF_ORIGINAL')
        f=max(choices,key=lambda f:(iso_date(f['filing_date']),f['accession_number']))
        amendments=p.get('/stocks/filings/vX/index',{'cik':row['cik'],'form_type.any_of':'10-K/A,10-Q/A','filing_date.gte':iso_date(f['filing_date']),'filing_date.lte':day,'limit':1})
        if amendments.get('results'):raise DataUnavailable('AS_OF_AMENDMENT_REQUIRES_REVIEW')
        entity=next(e['company_data'] for e in f['entities'] if e.get('relation')=='filer' and str(e['company_data']['cik']).zfill(10)==row['cik'])
        sic=str(entity.get('sic','')).zfill(4)
        row.update(metadata=f,sic=sic,division=division(sic),classification_vintage='UNCERTIFIED_PROVIDER_FILING_METADATA')
        if not division(sic):row.update(resolved=True,data_status='OUT_OF_SCOPE_INDUSTRY');return row
        parsed=urlparse(f['xbrl_instance_url'])
        if parsed.hostname not in ('api.massive.com','api.polygon.io') or parsed.query or not parsed.path.startswith('/v1/reference/sec/filings/'+f['id']+'/files/'):raise DataUnavailable('INVALID_ORIGINAL_URL')
        matches=list(root.glob(f['accession_number']+'-*.json'));raw=None
        if matches:
            saved=read_json(matches[0]);asset=root/saved['xml_asset']
            with gzip.open(asset,'rb') as stream:raw=stream.read()
            assert hashlib.sha256(raw).hexdigest()==saved['sha256']
        if raw is None:raw=p.get(parsed.path,xml=True)
        receipt=save_original(root,f,raw,datetime.now(timezone.utc).isoformat());facts=parse_historical(raw,receipt,row['cik'],decision)
        audit=audit_fundamental(raw,receipt,facts,row['cik'],decision)
        row.update(resolved=True,data_status='VERIFIED',fundamental=facts,receipt=receipt,audit=audit)
    except Exception as e:row.update(resolved=False,data_status='DATA_GAP',reason=str(e) if isinstance(e,DataUnavailable) else type(e).__name__)
    return row

def collect(day,root):
    source=read_json(root/(day+'.universe.json'));dest=root/(day+'.panel.json');old=read_json(dest) if dest.exists() else {};done={r['ticker']:r for r in old.get('rows',[])}
    original_root=root/'originals';original_root.mkdir(exist_ok=True)
    todo=[r for r in source['rows'] if r['ticker'] not in done]
    pool=concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        futures={pool.submit(original,r,day,original_root):r for r in todo}
        for f in concurrent.futures.as_completed(futures,timeout=420):
            row=f.result();done[row['ticker']]=row
            atomic_json(dest,dict(date=day,price_as_of=source['price_as_of'],rows=sorted(done.values(),key=lambda r:r['ticker']),completed=len(done),expected=len(source['rows'])))
            print('PANEL',day,len(done),len(source['rows']),row['ticker'],row['data_status'],flush=True)
    finally:pool.shutdown(wait=True,cancel_futures=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','collect']);p.add_argument('--cache',default='.history_market');p.add_argument('--out',default='history_output');p.add_argument('--day');a=p.parse_args();root=Path(a.out);root.mkdir(exist_ok=True)
    prepare(a.cache,root) if a.mode=='prepare' else collect(a.day,root)
