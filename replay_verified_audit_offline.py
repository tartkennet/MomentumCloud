"""Replay frozen audit inputs without network; unavailable requests fail closed."""
import gzip
import hashlib
import json
import os
import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
os.chdir(ROOT)
os.environ['POLYGON_API_KEY'] = 'OFFLINE_NO_NETWORK'
import backtest_momentum_v3 as engine
import run_one_verified_gap_model as audit

SNAPSHOT = ROOT / 'frozen_recovery/frozen/audit_request_snapshot'
def request_key(path, params):
    return json.dumps({'path':path,'params':params or {}},sort_keys=True,separators=(',',':'))

index_path=ROOT/'frozen_recovery/request_index.json'
if index_path.exists():
    index={key:Path(value) for key,value in json.loads(index_path.read_text()).items()}
else:
    index = {}
    for directory in (SNAPSHOT, ROOT/'evidence/selection/paired_action_evidence'):
        for file in directory.glob('*.json.gz'):
            with gzip.open(file) as source:
                record=json.load(source)
            index[request_key(record['request']['path'],record['request']['params'])]=file
    index_path.write_text(json.dumps({key:str(value) for key,value in index.items()}))

# Position reference windows can answer observed daily requests but MUST NOT
# override the long formation histories used to choose securities.
reference_rows=json.loads((ROOT/'evidence/selection/selection_reference_histories.json').read_text())
classified_rows=json.loads((ROOT/'classification/verified_ticker_histories.json').read_text())
for ticker,bases in classified_rows.items():
    reference_rows.setdefault(ticker,bases)
daily_quotes={}
for file in (ROOT/'audit_evidence/bulk_basis').glob('*.csv'):
    ticker,day,basis=file.stem.rsplit('_',2)
    with file.open() as source:
        daily_quotes[(ticker,day,basis)]=[{k:float(v) for k,v in row.items() if v!=''} for row in csv.DictReader(source)]

histories={}
for file in (ROOT/'universe_evidence').glob('histories_*.json'):
    histories.update(json.loads(file.read_text()))

def offline_get(self,path,params=None):
    key=request_key(path,params)
    if key in index:
        with gzip.open(index[key]) as source:
            return json.load(source)['response']
    pieces=path.split('/')
    if len(pieces)==10 and pieces[1:4]==['v2','aggs','ticker']:
        ticker,start,end=pieces[4],pieces[8],pieces[9]
        basis=str((params or {}).get('adjusted','true')).lower()
        if ticker in histories and basis in histories[ticker]:
            payload=histories[ticker][basis]
            if 'error_type' in payload:
                raise RuntimeError('OFFLINE_HISTORY_ERROR '+ticker)
            bars=[bar for bar in payload.get('results',[]) if start<=datetime.fromtimestamp(bar['t']/1000,timezone.utc).date().isoformat()<=end]
            return {'results':bars,'status':'OK','source':'frozen full individual history'}
        named_basis='adjusted' if basis=='true' else 'raw'
        if start==end and (ticker,start,named_basis) in daily_quotes:
            return {'results':daily_quotes[(ticker,start,named_basis)],'status':'OK','source':'direct observed paired action quote'}
        if ticker in reference_rows and named_basis in reference_rows[ticker]:
            rows=reference_rows[ticker][named_basis]
            if start==end and start in rows:
                row=rows[start]
                bar={key:row[field] for key,field in [('o','open'),('h','high'),('l','low'),('c','close'),('v','volume')]}
                bar['t']=int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp()*1000)
                return {'results':[bar],'status':'OK','source':'frozen observed price; not formation override'}
    raise RuntimeError('OFFLINE_REQUEST_MISSING '+key)

engine.PolygonClient._get=offline_get

class FrozenDateTime(datetime):
    @classmethod
    def now(cls,tz=None):
        return cls(2026,10,6,tzinfo=timezone.utc)
engine.datetime=FrozenDateTime

def frozen_cache(_path,*args,**kwargs):
    data=b''.join(file.read_bytes() for file in sorted((ROOT/'frozen_recovery').glob('cache*.bin')))
    assert hashlib.sha256(data).hexdigest()=='638589917ba5a37c0c69bdd0e057b4fb873618981c286bde3d88488135313ee2'
    payload=json.loads(data)
    # Preserve source provenance. New action successors are not inferred to exist:
    # absent execution requests still stop in offline_get.
    assert payload['version']==3 and payload['adjusted_through']=='2026-10-06'
    return payload['sessions'],payload['adjusted_through']
engine.load_backtest_cache=frozen_cache
engine.save_backtest_cache=lambda *args,**kwargs:None

if __name__=='__main__':
    audit.main()
