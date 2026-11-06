"""Resumable complete-universe price inventory; incomplete batches cannot rank."""
from pathlib import Path
from quality_forward import digest
from momentum_core_data import atomic_json,read_json


def scan(records, evaluate, cache, identity, batch_size=250):
    records=sorted(records,key=lambda r:r['ticker'])
    tickers=[r['ticker'] for r in records]
    if len(set(tickers))!=len(tickers):raise ValueError('DUPLICATE_UNIVERSE_SYMBOLS')
    key=digest(dict(identity=identity,universe=records,batch_size=batch_size))
    root=Path(cache)/'best-inventory-v1'/key;root.mkdir(parents=True,exist_ok=True)
    manifest=dict(schema_version=1,identity=identity,fingerprint=key,total_records=len(records),batch_size=batch_size,complete=False,batches=[])
    rows=[];excluded=[];resumed=0
    for start in range(0,len(records),batch_size):
        batch_records=records[start:start+batch_size];path=root/(str(start)+'.json')
        if path.exists():
            batch=read_json(path);resumed+=1
            assert batch['fingerprint']==key and batch['tickers']==tickers[start:start+batch_size]
            body={k:v for k,v in batch.items() if k!='sha256'}
            if digest(body)!=batch['sha256']:raise ValueError('CHANGED_INVENTORY_CHECKPOINT')
        else:
            found=[];rejected=[]
            for record in batch_records:
                row,reason=evaluate(record)
                if row is not None:found.append(row)
                else:rejected.append(dict(ticker=record['ticker'],reason=reason))
            batch=dict(fingerprint=key,start=start,end=start+len(batch_records),tickers=tickers[start:start+batch_size],rows=found,excluded=rejected)
            batch['sha256']=digest(batch);atomic_json(path,batch)
        if len(batch['rows'])+len(batch['excluded'])!=len(batch_records):raise ValueError('INCOMPLETE_INVENTORY_BATCH')
        if {r['ticker'] for r in batch['rows']+batch['excluded']}!=set(batch['tickers']):raise ValueError('INVENTORY_MEMBERSHIP_MISMATCH')
        rows.extend(batch['rows']);excluded.extend(batch['excluded'])
        manifest['batches'].append(dict(start=start,end=batch['end'],sha256=batch['sha256']))
        manifest['processed_records']=len(rows)+len(excluded)
        atomic_json(root/'manifest.json',manifest)
        print('BEST_INVENTORY',manifest['processed_records'],len(records),'resumed_batches',resumed,flush=True)
    if len(rows)+len(excluded)!=len(records):raise ValueError('INCOMPLETE_MARKET_INVENTORY')
    manifest.update(complete=True,resumed_batches=resumed,priced_records=len(rows),excluded_records=len(excluded))
    manifest['sha256']=digest(manifest);atomic_json(root/'manifest.json',manifest)
    return rows,excluded,manifest
