"""Read-only entitlement and primary-source probe; never a strategy/backtest."""
import gzip
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
import requests

OUT=Path('quality_inventory_output')
UA='MomentumCloudResearch/1.0 contact https://github.com/tartkennet/MomentumCloud/issues'


def probe(label,url,params=None,secret=False):
    stamp=datetime.now(timezone.utc).isoformat()
    result=dict(source=label,url=url,observed_at=stamp)
    try:
        r=requests.get(url,params=params,headers={'User-Agent':UA,'Accept':'application/json'},timeout=(5,20))
        result['http_status']=r.status_code
        if r.status_code==200:
            raw=r.content;payload=r.json();name=label+'.json.gz'
            with gzip.open(OUT/name,'wb') as f:f.write(raw)
            result.update(status='AVAILABLE',sha256=hashlib.sha256(raw).hexdigest(),asset=name)
            if 'facts' in payload:result.update(cik=payload.get('cik'),taxonomy_counts={k:len(v) for k,v in payload['facts'].items()})
            elif 'filings' in payload:result.update(cik=payload.get('cik'),sic=payload.get('sic'),recent_filing_count=len(payload['filings']['recent']['accessionNumber']))
            else:result['result_count']=len(payload.get('results',[]))
        else:result['status']='NOT_ENTITLED' if r.status_code in (401,403) and secret else 'HTTP_ERROR'
    except (requests.RequestException,ValueError) as e:result.update(status='FETCH_ERROR',error_type=type(e).__name__)
    return result


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    rows=[];key=os.environ.get('POLYGON_API_KEY')
    if key:
        for label,path,params in [
            ('app_income','/stocks/financials/v1/income-statements',{'tickers':'AAPL','timeframe':'quarterly','limit':1}),
            ('app_earnings_estimates','/benzinga/v1/earnings',{'ticker':'AAPL','limit':1}),
            ('app_filing_index','/stocks/filings/vX/index',{'ticker':'AAPL','limit':1})]:
            rows.append(probe(label,'https://api.polygon.io'+path,dict(params,apiKey=key),True))
    else:rows.append(dict(source='app_key',status='MISSING_SECRET'))
    for cik,label in [('0000320193','AAPL'),('0000789019','MSFT')]:
        rows.append(probe(label+'_submissions','https://data.sec.gov/submissions/CIK'+cik+'.json'))
        rows.append(probe(label+'_facts','https://data.sec.gov/api/xbrl/companyfacts/CIK'+cik+'.json'))
    report=dict(observed_at=datetime.now(timezone.utc).isoformat(),inventory_only=True,broker_orders_enabled=False,
        history_status='NOT_CERTIFIED',estimates_status='NO_VERIFIED_POINT_IN_TIME_REVISIONS',sources=rows)
    (OUT/'inventory.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
