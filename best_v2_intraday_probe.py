"""Read-only authenticated capability receipts. Never observes an account or creates fills."""
import json,os,requests,time
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
NY=ZoneInfo('America/New_York')

def main():
    now=datetime.now(timezone.utc);day=now.astimezone(NY).date().isoformat()
    start=datetime.fromisoformat(day+'T09:30:00').replace(tzinfo=NY)
    end=min(now,start.replace(hour=16))
    key=os.environ['POLYGON_API_KEY'];session=requests.Session();receipts=[]
    symbols=['SPY','SN','LFST','STGW','HNGE','CON','TBBB','FIGS','KYMR','GKOS','ATRC']
    for ticker in symbols:
        path=f'/v2/aggs/ticker/{ticker}/range/1/minute/{int(start.timestamp()*1000)}/{int(end.timestamp()*1000)}'
        r=session.get('https://api.polygon.io'+path,params={'apiKey':key,'adjusted':'false','sort':'desc','limit':3},timeout=(5,20))
        try:b=r.json()
        except ValueError:b={}
        rows=b.get('results',[])
        out=dict(ticker=ticker,path=path,observed_at=datetime.now(timezone.utc).isoformat(),http=r.status_code,status=b.get('status'),resultsCount=b.get('resultsCount'),count=len(rows),bars=rows[:3],provider_message_code='NOT_AUTHORIZED' if r.status_code==403 else None)
        receipts.append(out);print('BEST_V2_INTRADAY_CAPABILITY',json.dumps(out),flush=True)
    for label,path in [('snapshot','/v2/snapshot/locale/us/markets/stocks/tickers/SPY'),('grouped','/v2/aggs/grouped/locale/us/market/stocks/'+day)]:
        r=session.get('https://api.polygon.io'+path,params={'apiKey':key,'adjusted':'false','include_otc':'false'},timeout=(5,20))
        try:b=r.json()
        except ValueError:b={}
        result=b.get('ticker',{});rows=b.get('results',[])
        out=dict(source=label,path=path,observed_at=datetime.now(timezone.utc).isoformat(),http=r.status_code,status=b.get('status'),resultsCount=b.get('resultsCount'),count=len(rows),spy=next((x for x in rows if x.get('T')=='SPY'),None),snapshot={k:result.get(k) for k in ('ticker','min','lastTrade','updated')})
        receipts.append(out);print('BEST_V2_INTRADAY_CAPABILITY',json.dumps(out),flush=True)
    from pathlib import Path
    Path('intraday-capability.json').write_text(json.dumps(dict(paper_only=True,orders_sent=False,receipts=receipts),indent=2))
if __name__=='__main__':main()
