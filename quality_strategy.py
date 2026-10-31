"""Quality & Earnings v1: business improvement ranks, price confirmation only."""
import copy
import math
from collections import Counter
from research_stocks10 import fee

MODEL='momentum10-quality-earnings-net-v1'
PARAMETERS=dict(universe_size=100,min_price=10.,min_adv20=20_000_000.,history=253,relative_sessions=126,
    industry_slots=2,division_slots=4,max_position_weight=.20,max_industry_weight=.30,max_division_weight=.50,
    buy_limit_buffer=.02,execution_reserve=.0015,stress_execution_reserve=.003,initial_sek=20000.,
    filing_max_age_days=140,source_max_age_hours=24,rebalance='MONTHLY',individual_stop='NONE',global_regime='SPY_CLOSE_GT_SMA200')


def division(sic):
    x=int(sic)//100
    if 1<=x<=9:return 'Agriculture'
    if 10<=x<=14:return 'Mining'
    if 15<=x<=17:return 'Construction'
    if 20<=x<=39:return 'Manufacturing'
    if 40<=x<=48:return 'Transport/communications'
    if 50<=x<=51:return 'Wholesale'
    if 52<=x<=59:return 'Retail'
    if 70<=x<=89:return 'Services'
    return None


def rank(rows):
    good=[copy.deepcopy(r) for r in rows if r['fundamental']['qualified'] and division(r['sic'])]
    for key in ('revenue_growth','eps_growth','margin_change'):
        values=sorted(r['fundamental']['metrics'][key] for r in good)
        for r in good:
            value=r['fundamental']['metrics'][key]
            r.setdefault('rank_components',{})[key]=((sum(v<value for v in values)+.5*sum(v==value for v in values))/len(values))
    for r in good:r['quality_score']=sum(r['rank_components'].values())/3
    return sorted(good,key=lambda r:(-r['quality_score'],r['ticker']))


def choose(rows,nav):
    selected=[];industries=Counter();divisions=Counter();issuers=set();reserved=0.
    for row in rank(rows):
        industry=str(row['sic'])[:2];sector=division(row['sic']);p=row['price_usd']*1.02
        if row['cik'] in issuers or industries[industry]>=2 or divisions[sector]>=4:continue
        minimum=p+fee(p)
        if p>nav*.20 or reserved+minimum+(9-len(selected))*(10.2+fee(10.2))>nav:continue
        selected.append(row);reserved+=minimum;industries[industry]+=1;divisions[sector]+=1;issuers.add(row['cik'])
        if len(selected)==10:return selected
    return []


def plan_orders(targets,shares,nav,cash,prices=None):
    """Exact whole-share limit quantities committed BEFORE the opening price exists."""
    if len(targets)!=10:raise ValueError('TEN_REQUIRED')
    names={r['ticker']:r for r in targets};retained={t:q for t,q in shares.items() if t in names}
    if any(q<1 or not float(q).is_integer() for q in retained.values()):raise ValueError('CORPORATE_ENTITLEMENT_REQUIRES_REVIEW')
    # Quantities are committed now. Conservative expected sale proceeds
    # size conditional buys, but actual fills must use actual cleared cash.
    prices=prices or {r['ticker']:r['price_usd'] for r in targets}
    sales=[dict(ticker=t,side='SELL',quantity=math.floor(q),limit=None) for t,q in shares.items() if t not in names and q>=1]
    sale_reserve=sum(q*.98*prices[t]-fee(q*.98*prices[t]) for t,q in shares.items() if t not in names and q>=1)
    budget=cash+sale_reserve
    new=[r for r in targets if r['ticker'] not in retained]
    quantities={r['ticker']:1 for r in new};caps={r['ticker']:r['price_usd']*1.02 for r in targets}
    def value(t,q):return q*caps[t]
    def spend():return sum(value(t,q)+fee(value(t,q)) for t,q in quantities.items())
    def admissible():
        notionals={t:value(t,quantities.get(t,retained.get(t,0))) for t in names}
        if any(v>nav*.20+1e-8 for v in notionals.values()):return False
        return all(sum(v for t,v in notionals.items() if str(names[t]['sic'])[:2]==str(r['sic'])[:2])<=nav*.30+1e-8 and
                   sum(v for t,v in notionals.items() if division(names[t]['sic'])==division(r['sic']))<=nav*.50+1e-8 for r in targets)
    if spend()>budget+1e-8 or not admissible():raise ValueError('UNFUNDED_OR_RISK_LIMITED_MINIMUM_BASKET')
    while new:
        candidates=[]
        for r in new:
            t=r['ticker'];quantities[t]+=1
            if spend()<=budget+1e-8 and admissible():candidates.append(t)
            quantities[t]-=1
        if not candidates:break
        t=min(candidates,key=lambda t:(value(t,quantities[t]),t));quantities[t]+=1
    orders=sales+[dict(ticker=t,side='BUY',quantity=q,limit=caps[t]) for t,q in sorted(quantities.items())]
    return dict(orders=orders,reserved_cash_usd=spend(),sale_reserve_usd=sale_reserve,retained=retained,
                convention='Precommitted whole shares; no resizing at a future open; sell first; contingent buys require actual cash and the precommitted limit; never resize or borrow.')
