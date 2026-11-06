"""Whole-share funding AFTER BEST membership, with explicit group feasibility."""
import copy
import math
import momentum_core as core
from research_stocks10 import fee

CAPS={'ticker':20,'industry':35,'division':60,'cluster':50}


def cost(q,price):
    return q*price*1.02+fee(q*price*1.02) if q else 0.


def requirements(rows,fx):
    if len(rows)!=10 or len({r['cik'] for r in rows})!=10 or any(r.get('instrument_type')!='CS' or r['ticker']=='SPY' for r in rows):
        raise ValueError('TEN_COMMON_STOCKS_REQUIRED')
    if not math.isfinite(fx) or fx<=0:raise ValueError('INVALID_FX')
    charges={r['ticker']:math.ceil(cost(1,r['price_usd'])*fx*100) for r in rows}
    totals=[sum(charges.values())]
    for key,cap in CAPS.items():
        for r in rows:
            group=sum(charges[x['ticker']] for x in rows if x[key]==r[key])
            totals.append((group*100+cap-1)//cap)
    doubled=sum(math.ceil((r['price_usd']*1.02+2*fee(r['price_usd']*1.02))*fx*100) for r in rows)/100
    return dict(minimum_one_each_sek=sum(charges.values())/100,minimum_capital_sek=max(totals)/100,
                per_stock_cents=charges,doubled_friction_one_each_sek=doubled,caps=CAPS,usdsek=fx)


def orders(rows,shares,nav,cash,prices):
    if len(rows)!=10:raise ValueError('TEN_COMMON_STOCKS_REQUIRED')
    names={r['ticker']:r for r in rows};retained={t:q for t,q in shares.items() if t in names}
    if any(q<1 or not float(q).is_integer() for q in shares.values()):raise ValueError('CORPORATE_ENTITLEMENT_REQUIRES_REVIEW')
    sales=[dict(ticker=t,side='SELL',quantity=int(q)) for t,q in sorted(shares.items()) if t not in names]
    reserve=sum(q*.98*prices[t]-fee(q*.98*prices[t]) for t,q in shares.items() if t not in names)
    budget=cash+reserve;new=[r for r in rows if r['ticker'] not in retained]
    quantities={r['ticker']:1 for r in new}
    weights=core.capped_weights({r['ticker']:1/r['vol63'] for r in rows},.20)
    def exposure(t):return retained[t]*names[t]['price_usd']*1.02 if t in retained else cost(quantities[t],names[t]['price_usd'])
    def valid():
        if sum(cost(q,names[t]['price_usd']) for t,q in quantities.items())>budget+1e-8:return False
        return all(sum(exposure(x['ticker']) for x in rows if x[key]==r[key])<=nav*cap/100+1e-8 for key,cap in CAPS.items() for r in rows)
    if not valid():raise ValueError('UNFUNDED_OR_RISK_LIMITED_MINIMUM_BASKET')
    for r in new:
        t=r['ticker'];lo=1;hi=max(1,int(nav*weights[t]/(r['price_usd']*1.02)))
        while lo<hi:
            mid=(lo+hi+1)//2;quantities[t]=mid
            if valid():lo=mid
            else:hi=mid-1
        quantities[t]=lo
    return dict(orders=sales+[dict(ticker=t,side='BUY',quantity=q,limit=names[t]['price_usd']*1.02) for t,q in sorted(quantities.items())],
        retained=retained,reserved_cash_usd=sum(cost(q,names[t]['price_usd']) for t,q in quantities.items()),
        sale_reserve_usd=reserve,ideal_weights=weights)
