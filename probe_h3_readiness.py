"""Bounded read-only checks with existing credentials; never log secrets/URLs."""
import argparse
import json
import os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


def request(key,path,params):
    try:
        response=requests.get('https://api.polygon.io'+path,params=dict(params,apiKey=key),timeout=12)
        code=response.status_code
        if code!=200:return {'authorized':False,'http_status':code,'error':'RATE_LIMITED' if code==429 else 'ACCESS_DENIED_OR_UNAVAILABLE'}
        payload=response.json()
        result={'authorized':payload.get('status') in ('OK','DELAYED'),'http_status':code,
                'rows':len(payload.get('results') or [])}
        if '/aggs/ticker/SPY/' in path and result['rows']:
            dates=[datetime.fromtimestamp(r['t']/1000,timezone.utc).date().isoformat() for r in payload['results']]
            result['latest_observed_session']=max(dates)
        return result
    except Exception as exc:
        # Exception text and response bodies may contain credential-bearing URLs.
        return {'authorized':False,'error':type(exc).__name__}


def probe(live=False,previous=None,query=request):
    key=os.getenv('POLYGON_API_KEY')
    now=datetime.now(timezone.utc)
    report={'checked_at':now.isoformat(),'key_configured':bool(key),'live_probe':live,
            'secrets_exposed':False,'subscription_changed':False,'live_approved':False,'broker_orders_enabled':False}
    if not key:
        report.update(status='DATA_BLOCKED',error='POLYGON_API_KEY_NOT_CONFIGURED');return report
    if not live:
        report.update(status='CONFIGURED',last_live_probe=previous)
        return report
    end=(now.date()-timedelta(days=1)).isoformat();start=(now.date()-timedelta(days=11)).isoformat()
    specs={
        'raw_daily_bars':('/v2/aggs/ticker/SPY/range/1/day/'+start+'/'+end,{'adjusted':'false','sort':'desc','limit':10}),
        'dated_universe':('/v3/reference/tickers',{'date':end,'market':'stocks','type':'CS','active':'true','limit':1}),
        'splits':('/stocks/v1/splits',{'execution_date.lte':end,'limit':1}),
        'dividends':('/stocks/v1/dividends',{'ex_dividend_date.lte':end,'limit':1})}
    report['required_endpoints']={name:query(key,path,params) for name,(path,params) in specs.items()}
    # Quote access is optional for paper collection and mandatory to disclose
    # accurately. Never acquire or change a subscription to make this pass.
    observed=report['required_endpoints']['raw_daily_bars'].get('latest_observed_session',end)
    day=datetime.fromisoformat(observed).replace(hour=9,minute=30,tzinfo=ZoneInfo('America/New_York'))
    opening=int(day.timestamp()*1e9)
    report['optional_quotes']=query(key,'/v3/quotes/SPY',{'timestamp.gte':opening,'timestamp.lte':opening+60_000_000_000,
                                                        'sort':'timestamp','order':'asc','limit':1})
    ok=(all(r['authorized'] for r in report['required_endpoints'].values())
        and all(report['required_endpoints'][k].get('rows',0)>0 for k in ('raw_daily_bars','dated_universe')))
    report['status']='PASS' if ok else 'DATA_BLOCKED'
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--record-dir',required=True);p.add_argument('--live',action='store_true');args=p.parse_args()
    root=Path(args.record_dir);root.mkdir(parents=True,exist_ok=True);file=root/'H3_readiness.json'
    previous=json.loads(file.read_text()) if file.exists() else None
    # Retain the last real probe, not a recursively nested chain of no-op runs.
    if previous and not previous.get('live_probe'):previous=previous.get('last_live_probe')
    result=probe(args.live,previous)
    file.write_text(json.dumps(result,indent=2));print(json.dumps(result))
    if result['status']=='DATA_BLOCKED':raise SystemExit(1)
