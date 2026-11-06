"""Preregistered BEST v1 price-only signal; no capital or outcome optimization."""
import copy
import math
import statistics
from collections import Counter
from pathlib import Path
from quality_forward import digest
import momentum_core as core

MODEL='momentum10-best-v2'
PROTOCOL='docs/MOMENTUM10_BEST_V2_PROTOCOL.md'
PARAMETERS=dict(positions=10,min_price=10,min_adv20=20_000_000,history=253,
    score_weights=[25,20,15,10,10,15,5],strong_pool=60,sector_slots=2,
    cluster_slots=3,correlation=.85,issuer_cap=.15,sector_cap=.25,cluster_cap=.35,
    factor_slots=4,factor_cap=.45,min_vol=.08,vol_floor=.20,target_sek=25000)


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


def metrics(closes,spy,turnover):
    from best_strategy import metrics as established
    m=established(closes,spy)
    rs63=(closes[0]/closes[63])/(spy[0]/spy[63])-1
    rs21=(closes[0]/closes[21])/(spy[0]/spy[21])-1
    previous=(closes[21]/closes[63])/(spy[21]/spy[63])-1
    acceleration=math.log1p(rs21)-.5*math.log1p(previous)
    volume_ratio=statistics.fmean(turnover[:5])/statistics.fmean(turnover[5:25])
    confirmation=min(3.,volume_ratio)*min(1.1,closes[0]/max(closes[1:64]))
    gap=max(abs(closes[i]/closes[i+1]-1) for i in range(126))
    pin=(max(closes[:21])/min(closes[:21])-1)<.03 and gap>=.15
    m.update(rs63=rs63,rs21=rs21,acceleration=acceleration,volume_confirmation=confirmation,
        volume_ratio=volume_ratio,risk_adjusted=m['momentum_6_1']/max(.20,m['vol63']),
        sma50_prior=statistics.fmean(closes[21:71]),sma200_prior=statistics.fmean(closes[21:221]),
        extension50=closes[0]/m['sma50'],max_gap126=gap,price_pinned=pin)
    m['price_exclusions']=[code for condition,code in [
        (m['vol63']<.08,'ABNORMALLY_LOW_VOLATILITY'),(gap>=.35,'UNRESOLVED_ADJUSTED_PRICE_JUMP'),
        (pin,'PRICE_PINNING'),(m['extension50']>1.35 or m['return_1m']>.60 or m['return_3m']>1.50,'OVEREXTENDED')]
        if condition]
    m['strong']=bool(m['strong'] and rs63>0 and rs21>0 and m['persistence']>=.55
        and m['sma50']>m['sma50_prior'] and m['sma200']>m['sma200_prior'] and not m['price_exclusions'])
    return m


SCORE_KEYS=('rs12','rs6','rs63','acceleration','volume_confirmation','risk_adjusted','persistence')
def rank(rows):
    result=copy.deepcopy(rows);numerators={r['ticker']:0 for r in result}
    for weight,key in zip(PARAMETERS['score_weights'],SCORE_KEYS):
        values=[r[key] for r in result]
        for r in result:
            ordinal=2*sum(x<r[key] for x in values)+sum(x==r[key] for x in values)
            r.setdefault('components',{})[key]=ordinal/(2*len(values))
            numerators[r['ticker']]+=weight*ordinal
    for r in result:r['score']=numerators[r['ticker']]/(200*len(result))
    result.sort(key=lambda r:(-r['score'],-r['rs63'],r['ticker']))
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
        if r.get('event_status')=='EXCLUDED_PENDING_PRICE_BINDING_EVENT':
            skips.append(dict(ticker=r['ticker'],rank=r['universe_rank'],reason='PRICE_BINDING_CORPORATE_EVENT'));continue
        if any(x['cik']==r['cik'] for x in selected):reason='DUPLICATE_ISSUER'
        for key,limit in [('sector',2),('cluster',3),('factor',4)]:
            if sum(x[key]==r[key] for x in selected)>=limit:reason=key.upper()+'_CAP'
        if reason:skips.append(dict(ticker=r['ticker'],rank=r['universe_rank'],reason=reason));continue
        selected.append(copy.deepcopy(r))
        if len(selected)==10:break
    return selected if len(selected)==10 else [],skips


def evaluate_record(data,day,record,spy,expected):
    if record.get('ticker')=='SPY' or not core.eligible(record) or not record.get('cik'):return None,'NOT_ELIGIBLE_COMMON_STOCK'
    t=record['ticker'];history=data.history(day,t,253)
    if len(history)!=253 or [x[0] for x in history]!=expected or any(not b for _,b in history):return None,'INCOMPLETE_HISTORY'
    if any(core.number(b[1]) is None for _,b in history):return None,'INVALID_CLOSE'
    if history[0][1][1]<10:return None,'PRICE_BELOW_10'
    if any(core.number(b[2]) is None for _,b in history[:20]):return None,'INVALID_VOLUME'
    adv=statistics.fmean(b[1]*b[2] for _,b in history[:20])
    if adv<20_000_000:return None,'LIQUIDITY'
    try:m=metrics(core.adjusted_history(data,day,t,253),spy,[b[1]*b[2] for _,b in history[:25]])
    except ValueError as exc:return None,str(exc)
    return dict(ticker=t,cik=str(record['cik']).zfill(10),name=record.get('name',''),price_usd=history[0][1][1],
                adv20_usd=adv,instrument_type=record['type'],exchange=record['primary_exchange'],**m),None


def collect_prices(data, day, cache=None):
    spy=core.adjusted_history(data,day,'SPY',253)
    if len(spy)!=253:raise ValueError('INCOMPLETE_SPY_HISTORY')
    records=data.universe(day);rows=[];excluded=[]
    expected=[x[0] for x in data.history(day,'SPY',253)]
    evaluate=lambda record:evaluate_record(data,day,record,spy,expected)
    if cache is not None:
        from best_inventory import scan
        rows,excluded,inventory=scan(records,evaluate,cache,dict(day=day,protocol=fingerprint(),prices=data.input_fingerprint()))
    else:
        for record in records:
            row,reason=evaluate(record)
            if row is not None:rows.append(row)
            else:excluded.append(dict(ticker=record.get('ticker'),reason=reason))
        inventory=dict(complete=True,total_records=len(records),processed_records=len(records),resumed_batches=0)
    unique={}
    for row in sorted(rows,key=lambda r:(-r['adv20_usd'],r['ticker'])):
        if row['cik'] in unique:excluded.append(dict(ticker=row['ticker'],reason='DUPLICATE_ISSUER_CLASS'))
        else:unique[row['cik']]=row
    rows=list(unique.values());ranked=rank(rows)
    exclusions=Counter(r['reason'] for r in excluded)
    if len(ranked)+len(excluded)!=len(records):raise ValueError('UNACCOUNTED_UNIVERSE_RECORDS')
    return ranked,dict(reference_records=len(records),priced_liquid=len(rows),strong=sum(r['strong'] for r in ranked),
        exclusions=dict(exclusions),excluded_names=excluded,adv_truncation=False,inventory=inventory,
        scope='Dated provider US common-stock reference; eligible XNAS/XNYS/XASE; no historical performance claim',
        exchange_counts=dict(Counter(r.get('primary_exchange') or 'UNKNOWN' for r in records))),spy[0]>statistics.fmean(spy[:200])
