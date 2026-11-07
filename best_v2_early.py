"""Preregistered E1 WATCHLIST, evaluated identically for every liquid issuer."""
import math,statistics,hashlib
from pathlib import Path
from quality_forward import digest
PARAMETERS=dict(prior_drawdown=-.15,rs21=.03,volume_ratio=1.2,max_vol=.80,max_extension20=1.2,max_return21=.40,confirmation10=.8,breakout63=.99)

def fingerprint():return digest(dict(component='E1_WATCHLIST',parameters=PARAMETERS,protocol=hashlib.sha256(Path('docs/MOMENTUM10_BEST_V2_PROTOCOL.md').read_bytes()).hexdigest()))

def evaluate(c,spy,m):
    sma20=statistics.fmean(c[:20]);sma20_prior=statistics.fmean(c[10:30]);sma50_prior=statistics.fmean(c[10:60])
    confirmation=sum(c[i]>statistics.fmean(c[i:i+20]) for i in range(10))/10
    drawdown=min(c[21:127])/max(c[21:253])-1
    breakout=c[0]/max(c[1:64]);extension=c[0]/sma20
    tests=dict(prior_decline=drawdown<=-.15,price_above_rising_averages=c[0]>sma20>m['sma50'] and sma20>sma20_prior and m['sma50']>sma50_prior,
        relative_strength=m['rs21']>=.03 and m['rs63']>0,acceleration=m['acceleration']>0,
        confirmation=confirmation>=.8,breakout=breakout>=.99,volume=m['volume_ratio']>=1.2,
        risk=m['vol63']<=.80 and extension<=1.2 and m['return_1m']<=.40 and not m['price_exclusions'])
    return dict(component='E1_WATCHLIST',qualified=all(tests.values()),tests=tests,failed=[k for k,v in tests.items() if not v],
        prior_drawdown=drawdown,sma20=sma20,sma20_prior=sma20_prior,confirmation10=confirmation,breakout63=breakout,extension20=extension)

def rank(rows):
    keys=('rs21','rs63','acceleration','volume_confirmation','confirmation10');weights=(30,25,20,15,10)
    n=len(rows);out=[]
    for r in rows:
        values=dict(r,confirmation10=r['early']['confirmation10']);total=0
        for k,w in zip(keys,weights):
            population=[x['early']['confirmation10'] if k=='confirmation10' else x[k] for x in rows]
            total+=w*(2*sum(v<values[k] for v in population)+sum(v==values[k] for v in population))
        out.append(dict(ticker=r['ticker'],score=total/(200*n),qualified=r['early']['qualified'],failed=r['early']['failed'],
            rs21=r['rs21'],rs63=r['rs63'],acceleration=r['acceleration'],volume_ratio=r['volume_ratio'],**{k:r['early'][k] for k in ('prior_drawdown','confirmation10','breakout63','extension20')}))
    return sorted(out,key=lambda x:(-x['score'],-x['rs63'],x['ticker']))

def established_reasons(c,m):
    tests={k:m[k]>0 for k in ('momentum_12_1','momentum_6_1','rs6','rs63','rs21')}
    tests.update(close_above_sma50=c[0]>m['sma50'],sma50_above_sma200=m['sma50']>m['sma200'],rising_sma50=m['sma50']>m['sma50_prior'],rising_sma200=m['sma200']>m['sma200_prior'],persistence=m['persistence']>=.55)
    return [k for k,v in tests.items() if not v]+m['price_exclusions']

def diagnose(data,ticker,day):
    import momentum_core as core
    from best_v2_strategy import metrics
    def one(d):
        c=core.adjusted_history(data,d,ticker,253);b=core.adjusted_history(data,d,'SPY',253);h=data.history(d,ticker,253)
        if len(c)!=253 or len(b)!=253 or any(not x or not core.number(x[2]) for _,x in h[:25]):return dict(date=d,status='INCOMPLETE_HISTORY')
        m=metrics(c,b,[x[1]*x[2] for _,x in h[:25]])
        return dict(date=d,status='COMPLETE_PRICE_DATA',established=m['strong'],established_rejection_reasons=established_reasons(c,m),
            early=evaluate(c,b,m),metrics={k:m[k] for k in ('momentum_12_1','momentum_6_1','rs6','rs21','rs63','acceleration','vol63','sma50','sma200','sma50_prior','sma200_prior','volume_ratio')},price_usd=h[0][1][1])
    days=[d for d in data.sessions if d<=day][-126:];history=[one(d) for d in days]
    current=one(day);first=next((x['date'] for x in history if x.get('early',{}).get('qualified')),None)
    first_established=next((x['date'] for x in history if x.get('established')),None)
    return dict(ticker=ticker,component_fingerprint=fingerprint(),current=current,first_early_in_window=first,first_established_in_window=first_established,
        window_start=days[0] if days else None,window_end=day,complete_days=sum(x['status']=='COMPLETE_PRICE_DATA' for x in history),history=history,
        interpretation='Retrospective mechanism check with fixed E1 rules, not historical execution or out-of-sample performance; current universe, no historical return claim.')
