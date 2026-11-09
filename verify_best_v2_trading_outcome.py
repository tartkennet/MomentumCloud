"""Read-only business acceptance, after durable journal publication."""
import json,urllib.request,sys
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

def main():
    url='https://raw.githubusercontent.com/tartkennet/MomentumCloud/best-v2-observed-snapshots/public/data/momentum-best-v2.json'
    with urllib.request.urlopen(url,timeout=30) as response:r=json.load(response)
    p=r['paper'];out=p.get('trading_outcome') or {};miss=p.get('last_missed_execution');today=datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    print('BEST_V2_TRADING_OUTCOME',json.dumps(dict(technical_ready=r.get('technical_readiness',{}).get('status'),outcome=out,missed=miss,paper_started=p['paper_started'])),flush=True)
    failed=(miss and miss['session']==today) or out.get('status') in ('OPEN_PRICE_UNAVAILABLE','OPEN_PRICE_PROVIDER_DELAY','MISSED_OPEN_NO_BACKFILL')
    if failed:
        print('::error title=Paper execution blocked::No paper execution success is asserted. Inspect per-order reasons; no backfill.')
        return 1
    if out.get('status')=='FILLED':assert out['filled']==len(out['orders']) and all(o['status']=='FILLED' for o in out['orders'])
    return 0
if __name__=='__main__':sys.exit(main())
