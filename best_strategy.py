"""Preregistered BEST v1 price-only signal; no capital or outcome optimization."""
import copy
import math
import statistics
from collections import Counter
from pathlib import Path
from quality_forward import digest
import momentum_core as core

MODEL='momentum10-best-v1'
PROTOCOL='docs/MOMENTUM10_BEST_PROTOCOL_V1.md'
PARAMETERS=dict(positions=10,min_price=10,min_adv20=20_000_000,history=253,
    score_weights=[.35,.25,.25,.15],strong_pool=40,industry_slots=3,division_slots=6,
    cluster_slots=4,correlation=.85,issuer_cap=.20,industry_cap=.35,division_cap=.60,cluster_cap=.50)


def fingerprint():
    import hashlib
    return digest(dict(model=MODEL,parameters=PARAMETERS,protocol_sha256=hashlib.sha256(Path(PROTOCOL).read_bytes()).hexdigest()))


def division(sic):
    n=int(sic)//100
    for low,high,name in [(1,9,'Agriculture'),(10,14,'Mining'),(15,17,'Construction'),(20,39,'Manufacturing'),
        (40,48,'Transport/communications'),(49,49,'Utilities'),(50,51,'Wholesale'),(52,59,'Retail'),
        (60,67,'Finance/insurance/realestate'),(70,89,'Services')]:
        if low<=n<=high:return name
    raise ValueError('UNVERIFIED_INDUSTRY_CLASSIFICATION')


def metrics(closes, spy):
    if len(closes)!=253 or len(spy)!=253 or any(not math.isfinite(c) or c<=0 for c in closes+spy):
        raise ValueError('INCOMPLETE_OR_INVALID_CLOSES')
    returns=[closes[i]/closes[i+1]-1 for i in range(63)]
    vol=statistics.stdev(returns)*math.sqrt(252)
    if not math.isfinite(vol) or vol<=0:raise ValueError('NONPOSITIVE_VOLATILITY')
    m12=closes[21]/closes[252]-1;m6=closes[21]/closes[126]-1
    return dict(momentum_12_1=m12,momentum_6_1=m6,rs12=(1+m12)/(spy[21]/spy[252])-1,
        rs6=(1+m6)/(spy[21]/spy[126])-1,vol63=vol,risk_adjusted=m6/vol,
        persistence=sum(closes[i]>statistics.fmean(closes[i:i+50]) for i in range(63))/63,
        return_3m=closes[0]/closes[63]-1,return_1m=closes[0]/closes[21]-1,
        sma50=statistics.fmean(closes[:50]),sma200=statistics.fmean(closes[:200]),returns63=returns,
        strong=bool(m12>0 and m6>0 and (1+m6)>spy[21]/spy[126] and closes[0]>statistics.fmean(closes[:50])>statistics.fmean(closes[:200]) and closes[0]>closes[63]))


def rank(rows):
    result=copy.deepcopy(rows)
    for key in ('rs12','rs6','risk_adjusted','persistence'):
        values=sorted(r[key] for r in result)
        for r in result:r.setdefault('components',{})[key]=(sum(x<r[key] for x in values)+.5*sum(x==r[key] for x in values))/len(values)
    for r in result:r['score']=sum(w*r['components'][k] for w,k in zip(PARAMETERS['score_weights'],('rs12','rs6','risk_adjusted','persistence')))
    result.sort(key=lambda r:(-r['score'],-r['rs6'],r['ticker']))
    for i,r in enumerate(result):r['universe_rank']=i+1
    return result


def clusters(rows):
    parent={r['ticker']:r['ticker'] for r in rows}
    def root(t):
        while parent[t]!=t:t=parent[t]
        return t
    edges=[]
    for i,a in enumerate(rows):
        for b in rows[:i]:
            rho=statistics.correlation(a['returns63'],b['returns63'])
            if rho>=PARAMETERS['correlation']:
                aa,bb=sorted([root(a['ticker']),root(b['ticker'])]);parent[bb]=aa
                edges.append(dict(a=a['ticker'],b=b['ticker'],correlation=rho))
    for r in rows:r['cluster']=root(r['ticker'])
    return edges


def select(rows):
    selected=[];skips=[]
    for r in rows:
        reason=None
        if any(x['cik']==r['cik'] for x in selected):reason='DUPLICATE_ISSUER'
        for key,limit in [('industry',3),('division',6),('cluster',4)]:
            if sum(x[key]==r[key] for x in selected)>=limit:reason=key.upper()+'_CAP'
        if reason:skips.append(dict(ticker=r['ticker'],rank=r['universe_rank'],reason=reason));continue
        selected.append(copy.deepcopy(r))
        if len(selected)==10:break
    return selected if len(selected)==10 else [],skips


def collect_prices(data, day):
    spy=core.adjusted_history(data,day,'SPY',253)
    if len(spy)!=253:raise ValueError('INCOMPLETE_SPY_HISTORY')
    records=data.universe(day);rows=[];exclusions=Counter();excluded=[];expected=[x[0] for x in data.history(day,'SPY',253)]
    for record in records:
        if record.get('ticker')=='SPY' or not core.eligible(record) or not record.get('cik'):exclusions['NOT_ELIGIBLE_COMMON_STOCK']+=1;excluded.append(dict(ticker=record.get('ticker'),reason='NOT_ELIGIBLE_COMMON_STOCK'));continue
        t=record['ticker'];history=data.history(day,t,253)
        if len(history)!=253 or [x[0] for x in history]!=expected or any(not b for _,b in history):
            exclusions['INCOMPLETE_HISTORY']+=1;excluded.append(dict(ticker=record.get('ticker'),reason='INCOMPLETE_HISTORY'));continue
        if any(core.number(b[1]) is None for _,b in history):exclusions['INVALID_CLOSE']+=1;excluded.append(dict(ticker=record.get('ticker'),reason='INVALID_CLOSE'));continue
        if history[0][1][1]<10:exclusions['PRICE_BELOW_10']+=1;excluded.append(dict(ticker=record.get('ticker'),reason='PRICE_BELOW_10'));continue
        if any(core.number(b[2]) is None for _,b in history[:20]):exclusions['INVALID_VOLUME']+=1;excluded.append(dict(ticker=record.get('ticker'),reason='INVALID_VOLUME'));continue
        adv=statistics.fmean(b[1]*b[2] for _,b in history[:20])
        if adv<20_000_000:exclusions['LIQUIDITY']+=1;excluded.append(dict(ticker=record.get('ticker'),reason='LIQUIDITY'));continue
        c=core.adjusted_history(data,day,t,253)
        try:m=metrics(c,spy)
        except ValueError as exc:exclusions[str(exc)]+=1;excluded.append(dict(ticker=t,reason=str(exc)));continue
        rows.append(dict(ticker=t,cik=str(record['cik']).zfill(10),name=record.get('name',''),price_usd=history[0][1][1],
                         adv20_usd=adv,instrument_type=record['type'],exchange=record['primary_exchange'],**m))
    unique={}
    for row in sorted(rows,key=lambda r:(-r['adv20_usd'],r['ticker'])):
        if row['cik'] in unique:exclusions['DUPLICATE_ISSUER_CLASS']+=1;excluded.append(dict(ticker=row['ticker'],reason='DUPLICATE_ISSUER_CLASS'))
        else:unique[row['cik']]=row
    rows=list(unique.values())
    ranked=rank(rows)
    return ranked,dict(reference_records=len(records),priced_liquid=len(rows),strong=sum(r['strong'] for r in ranked),
                            exclusions=dict(exclusions),excluded_names=excluded,adv_truncation=False),spy[0]>statistics.fmean(spy[:200])
