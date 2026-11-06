"""Independent checks: no selector/ranker imports; independent numeric formulas."""
import math
from decimal import Decimal, ROUND_CEILING
from fractions import Fraction
import numpy as np
from quality_forward import digest
from quality_account_audit import audit_account
from audit_avanza10 import check as audit_sek


def signal(report):
    rows=report['ranked_liquid'];scores=[]
    for row in rows:
        comp={};exact={}
        for k in ('rs12','rs6','rs63','acceleration','volume_confirmation','risk_adjusted','persistence'):
            values=[r[k] for r in rows]
            comp[k]=(sum(v<row[k] for v in values)+sum(v==row[k] for v in values)/2)/len(values)
            exact[k]=Fraction(2*sum(v<row[k] for v in values)+sum(v==row[k] for v in values),2*len(values))
            assert abs(comp[k]-row['components'][k])<1e-10
        score=sum(Fraction(w,100)*exact[k] for w,k in zip((25,20,15,10,10,15,5),('rs12','rs6','rs63','acceleration','volume_confirmation','risk_adjusted','persistence')))
        assert abs(score-row['score'])<1e-10;scores.append((score,row['rs63'],row['ticker']))
    assert [r['ticker'] for r in rows]==[r[2] for r in sorted(scores,key=lambda x:(-x[0],-x[1],x[2]))]
    assert len({r['cik'] for r in rows})==len(rows)
    assert [r['ticker'] for r in report['strong_pool']]==[r['ticker'] for r in rows if r['strong']][:60]
    pool=report['strong_pool'];parents={r['ticker']:r['ticker'] for r in pool}
    def root(t):
        while parents[t]!=t:t=parents[t]
        return t
    for i,a in enumerate(pool):
        for b in pool[:i]:
            if np.corrcoef(a['returns63'],b['returns63'])[0,1]>=.85:
                aa,bb=sorted([root(a['ticker']),root(b['ticker'])]);parents[bb]=aa
    chosen=[]
    for r in pool:
        assert r['cluster']==root(r['ticker'])
        if r.get('event_status')=='EXCLUDED_PENDING_PRICE_BINDING_EVENT':continue
        if any(x['cik']==r['cik'] for x in chosen):continue
        if any(sum(x[k]==r[k] for x in chosen)>=limit for k,limit in [('sector',2),('cluster',3),('factor',4)]):continue
        chosen.append(r)
        if len(chosen)==10:break
    expected=chosen if len(chosen)==10 else []
    assert [x['ticker'] for x in report['targets']]==[x['ticker'] for x in expected]
    for row in report['targets']:
        assert row['event_status']=='CLEAR'
        assert row['instrument_type']=='CS' and row['ticker']!='SPY' and row['strong']
        assert row['momentum_12_1']>0 and row['momentum_6_1']>0 and row['rs6']>0 and row['return_3m']>0
    return dict(status='PASS',independent_code=True,candidates=len(rows),targets=len(expected))


def price_metrics(row, closes, spy, turnover):
    c=np.array(closes,dtype=float);b=np.array(spy,dtype=float);v=np.array(turnover,dtype=float)
    values=dict(momentum_12_1=c[21]/c[252]-1,momentum_6_1=c[21]/c[126]-1,
        rs12=(c[21]/c[252])/(b[21]/b[252])-1,rs6=(c[21]/c[126])/(b[21]/b[126])-1,
        rs63=(c[0]/c[63])/(b[0]/b[63])-1,rs21=(c[0]/c[21])/(b[0]/b[21])-1,
        vol63=np.std(c[:63]/c[1:64]-1,ddof=1)*np.sqrt(252),
        persistence=np.mean([c[i]>np.mean(c[i:i+50]) for i in range(63)]),
        sma50=np.mean(c[:50]),sma200=np.mean(c[:200]),return_3m=c[0]/c[63]-1,return_1m=c[0]/c[21]-1,
        sma50_prior=np.mean(c[21:71]),sma200_prior=np.mean(c[21:221]))
    values.update(acceleration=np.log1p(values['rs21'])-.5*np.log((c[21]/c[63])/(b[21]/b[63])),
        risk_adjusted=values['momentum_6_1']/max(.20,values['vol63']),
        volume_confirmation=min(3.,np.mean(v[:5])/np.mean(v[5:25]))*min(1.1,c[0]/np.max(c[1:64])),
        max_gap126=np.max(np.abs(c[:126]/c[1:127]-1)),extension50=c[0]/values['sma50'])
    pin=np.max(c[:21])/np.min(c[:21])-1<.03 and values['max_gap126']>=.15
    bad=values['vol63']<.08 or values['max_gap126']>=.35 or pin or values['extension50']>1.35 or values['return_1m']>.60 or values['return_3m']>1.5
    strong=bool(not bad and all(values[k]>0 for k in ('momentum_12_1','momentum_6_1','rs6','rs63','rs21')) and c[0]>values['sma50']>values['sma200'] and values['sma50']>values['sma50_prior'] and values['sma200']>values['sma200_prior'] and values['persistence']>=.55)
    assert strong==row['strong']
    for k,x in values.items():assert math.isclose(row[k],float(x),rel_tol=1e-9,abs_tol=1e-9),(row['ticker'],k)


def funding(rows, fx, result):
    charges={}
    for r in rows:
        n=Decimal(str(r['price_usd']))*Decimal('1.02')
        exact=(n+max(Decimal(1),n*Decimal('.0025'))+n*Decimal('.004'))*Decimal(str(fx))*100
        cents=int(exact.to_integral_value(rounding=ROUND_CEILING));actual=result['per_stock_cents'][r['ticker']]
        assert cents<=actual<=cents+1;charges[r['ticker']]=actual
    expected=max([sum(charges.values())]+[
        math.ceil(sum(charges[x['ticker']] for x in rows if x[k]==r[k])*100/cap)
        for k,cap in [('ticker',15),('sector',25),('cluster',35),('factor',45)] for r in rows])
    assert result['minimum_capital_sek']==expected/100
    assert result['minimum_one_each_sek']==sum(charges.values())/100
    return dict(status='PASS',independent_code=True)


def plan(rows, p, shares, nav, cash, prices):
    names={r['ticker']:r for r in rows};buys={};sales={}
    def cost(q,price):
        n=q*price*1.02
        return n+max(1,n*.0025)+n*.004
    for o in p['orders']:
        assert type(o['quantity']) is int and o['quantity']>0 and o['ticker']!='SPY'
        if o['side']=='BUY':
            assert o['ticker'] not in shares;assert o['limit']==names[o['ticker']]['price_usd']*1.02
            buys[o['ticker']]=o['quantity']
        else:sales[o['ticker']]=o['quantity']
    assert sales=={t:int(q) for t,q in shares.items() if t not in names}
    reserved=sum(q*prices[t]*.98-(max(1,q*prices[t]*.98*.0025)+q*prices[t]*.98*.004) for t,q in sales.items())
    spent=sum(cost(q,names[t]['price_usd']) for t,q in buys.items())
    assert abs(spent-p['reserved_cash_usd'])<1e-7 and spent<=cash+reserved+1e-7
    assert all(shares.get(t,0)>=1 or buys.get(t,0)>=1 for t in names)
    assert p['retained']=={t:q for t,q in shares.items() if t in names}
    exposures={t:(shares[t]*r['price_usd']*1.02 if t in shares else cost(buys[t],r['price_usd'])) for t,r in names.items()}
    for key,cap in [('ticker',.15),('sector',.25),('cluster',.35),('factor',.45)]:
        for r in rows:assert sum(exposures[x['ticker']] for x in rows if x[key]==r[key])<=nav*cap+1e-7
    return dict(status='PASS',independent_code=True,whole_shares=True)


def account(state, report):
    audits={k:audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
    cfg=state['capital_configuration']
    if cfg['mode']=='AUTO_TARGET_25000':assert cfg['initial_sek']==max(25000.,cfg['funding']['minimum_capital_sek'])
    audit_sek(state,report)
    assert report['journal_sha256']==digest(state)
    return dict(status='PASS',independent_code=True,ledger=audits)


def population(data, day, ranked):
    """Reconstruct the whole price-eligible universe without the selector."""
    from audit_core_normalized import closes_at
    expected={};dates=[r[0] for r in data.history(day,'SPY',253)]
    for record in data.universe(day):
        t=record.get('ticker');name=str(record.get('name','')).upper()
        if not t or t=='SPY' or record.get('active') is not True or record.get('type')!='CS' or not record.get('cik') or record.get('primary_exchange') not in ('XNAS','XNYS','XASE') or any(s in name for s in ('ACQUISITION','BLANK CHECK',' SPAC')):continue
        history=data.history(day,t,253)
        if len(history)!=253 or [r[0] for r in history]!=dates or any(not b for _,b in history):continue
        try:
            close=[float(b[1]) for _,b in history];volume=[float(b[2]) for _,b in history[:20]]
        except (TypeError,ValueError):continue
        if any(not math.isfinite(v) or v<=0 for v in close+volume) or close[0]<10:continue
        adv=math.fsum(c*v for c,v in zip(close[:20],volume))/20
        if adv<20_000_000:continue
        adjusted=closes_at(data,day,t,253)
        if len(adjusted)!=253 or np.std(np.array(adjusted[:63])/np.array(adjusted[1:64])-1,ddof=1)<=0:continue
        cik=str(record['cik']).zfill(10);old=expected.get(cik)
        if old is None or (-adv,t)<(-old[0],old[1]):expected[cik]=(adv,t)
    assert {r['ticker'] for r in ranked}=={r[1] for r in expected.values()}
    return dict(status='PASS',independent_code=True,complete_price_universe=True,eligible=len(expected))
