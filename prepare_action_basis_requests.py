"""Collect every missing paired daily action quote before another model run."""
import json
from pathlib import Path
from datetime import datetime,timezone
import run_v4_ablation_and_simple_candidate as model

p=Path('frozen_recovery')
payload=json.loads(b''.join(f.read_bytes() for f in sorted(p.glob('cache*.bin'))))
cache=payload['sessions']
sources={}
for f in Path('universe_evidence').glob('histories*.json'):
    sources.update(json.loads(f.read_text()))
ref=json.loads(Path('evidence/selection/selection_reference_histories.json').read_text())
ref.update(json.loads(Path('classification/verified_ticker_histories.json').read_text()))
requests=[]
for ticker,action in {**model.engine.CASH_CORPORATE_ACTIONS,**model.engine.STOCK_CORPORATE_ACTIONS}.items():
    day=action['effective_date']
    dates=sorted(k for k,v in cache.items() if k<day and ticker in v)
    if ticker in sources:
        bars=sources[ticker]['true'].get('results',[])
        dates=sorted(datetime.fromtimestamp(b['t']/1000,timezone.utc).date().isoformat() for b in bars if datetime.fromtimestamp(b['t']/1000,timezone.utc).date().isoformat()<day)
    if not dates:
        continue
    original=dates[-1]
    if ticker not in sources and not all(original in ref.get(ticker,{}).get(b,{}) for b in ['raw','adjusted']):
        requests.append(dict(ticker=ticker,day=original,purpose='original-basis',action=ticker))
    successor=action.get('successor_ticker')
    if successor and successor not in sources:
        dates=sorted(k for k,v in cache.items() if k>=day and successor in v)
        if dates:
            requests.append(dict(ticker=successor,day=dates[0],purpose='successor-basis',action=ticker))
unique={(r['ticker'],r['day']):r for r in requests}
Path('audit_evidence/basis_requests_bulk.json').write_text(json.dumps(list(unique.values()),indent=2)+'\n')
print('all action basis requests',len(unique),flush=True)
