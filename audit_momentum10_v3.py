"""Independent v3 signal and inherited execution policy audit; no v3 strategy import."""
import math
from collections import defaultdict
from audit_core_normalized import closes_at,positive
from audit_stocks10 import audit as cash_audit,financial_audit,near
from audit_momentum10_v2 import independent_fx,native_account,sigma

def population(data, day, config, stage):
    """Reconstruct the entire eligible set, including excluded top raw winners."""
    records = {r.get('ticker'): r for r in data.universe(day)}
    rows = []
    for ticker, record in sorted(records.items(), key=lambda x: str(x[0])):
        name = str(record.get('name', '')).upper()
        if (record.get('active') is not True or record.get('type') != 'CS'
                or record.get('primary_exchange') not in {'XNAS', 'XNYS', 'XASE'}
                or not ticker or any(s in name for s in ('ACQUISITION', 'BLANK CHECK', ' SPAC'))):
            continue
        history = data.history(day, ticker, 253)
        if len(history) != 253 or any(not bar for _, bar in history):
            continue
        price = positive(history[0][1][1])
        if price is None or price < config.min_price:
            continue
        dollars = []
        for _, bar in history[:20]:
            close, volume = positive(bar[1]), positive(bar[2], zero=True)
            if close is not None and volume is not None:
                dollars.append(close * volume)
        if len(dollars) != 20:
            continue
        adv = math.fsum(dollars) / 20
        if adv < config.min_adv:
            continue
        closes = closes_at(data, day, ticker, 253)
        if not closes:
            continue
        momentum=closes[0]/closes[126]-1
        x=[closes[i]/closes[i+1]-1 for i in range(126)]
        def deviation(z):
            center=math.fsum(z)/len(z)
            return math.sqrt(math.fsum((a-center)**2 for a in z)/(len(z)-1))
        vol=deviation(x);recent=deviation(x[:63]);sma=math.fsum(closes[:63])/63
        r1=closes[0]/closes[21]-1;r3=closes[0]/closes[63]-1
        if momentum<=0 or r1<=0 or r3<=0 or vol<=0 or recent<=0:continue
        if stage!='R' and closes[0]<=sma:continue
        rows.append(dict(ticker=ticker,raw_price=price,adv20_usd=adv,daily_volatility=recent,
            momentum_6m=momentum,score_volatility=vol,risk_normalized_score=momentum/vol,
            return_1m=r1,return_3m=r3,sma63=sma,_returns=x[:63]))
    return sorted(rows,key=lambda r:(-r['risk_normalized_score'],r['ticker']))

def independently_choose(rows,stage):
    selected=[]
    def correlation(a,b):
        ca=math.fsum(a)/63;cb=math.fsum(b)/63
        numerator=math.fsum((x-ca)*(y-cb) for x,y in zip(a,b))
        denominator=math.sqrt(math.fsum((x-ca)**2 for x in a)*math.fsum((y-cb)**2 for y in b))
        return numerator/denominator
    for row in rows:
        trial=selected+[row]
        if stage=='D':
            neighbors={i:set() for i in range(len(trial))}
            for i in neighbors:
                for j in range(i):
                    if correlation(trial[i]['_returns'],trial[j]['_returns'])>=.70:
                        neighbors[i].add(j);neighbors[j].add(i)
            seen=set();largest=0
            for i in neighbors:
                if i in seen:continue
                component=set();stack=[i]
                while stack:
                    j=stack.pop()
                    if j in component:continue
                    component.add(j);stack.extend(neighbors[j]-component)
                seen.update(component);largest=max(largest,len(component))
            if largest>2:continue
        selected.append(row)
        if len(selected)==10:return selected
    return []

def audit(data,config,s,b,metrics,memo):
    # The established independent event/cash verifier is reused, with policy
    # checks below replacing its old top-up/all-target fill assumptions.
    if '__fx' not in memo:memo['__fx']=independent_fx(data)
    fx=memo['__fx']
    account = native_account(data,config,s,fx)
    benchmark = cash_audit(data,config,b,benchmark=True)
    finance = financial_audit(s,b,metrics)
    assert not any(t['ticker']=='SPY' and t['side'] in ('BUY','SELL') for t in s.trades)
    days = [r['date'] for r in s.equity]
    daily = {r['date']:r for r in s.decisions}
    assert list(daily)==days
    selections = {r['date']:r for r in s.targets if r['risk_on']}
    stops = defaultdict(list)
    for e in s.stop_events:
        stops[e['date']].append(e)
    by_day = defaultdict(list)
    for t in s.trades:
        by_day[t['date']].append(t)
    splits,divs = defaultdict(list),defaultdict(list)
    for e in data.source.splits:splits[e['execution_date']].append(e)
    for e in data.source.dividends:divs[e['ex_dividend_date']].append(e)
    shares,refs,blacklist,queued = {},{},{},{}
    adjustments={}
    previous_on,seen = False,''
    pending_selection = None
    blocked = {e['date'] for e in s.blocked}
    retained_checks,stop_fills,signals = 0,0,0
    for day in days:
        bars=data.bars(day)
        for e in splits[day]:
            t=e['ticker'];ratio=e['split_to']/e['split_from']
            if t in shares:shares[t]*=ratio
            if t in refs:refs[t]=[v/ratio for v in refs[t]]
            for a in adjustments.get(t,[]):a['face']/=ratio;a['usd']/=ratio
        for t,items in list(adjustments.items()):
            if t not in refs:adjustments.pop(t);continue
            remaining=[]
            for a in items:
                usd=a['face']*fx(day,a['currency']);refs[t][1]-=usd-a['usd'];a['usd']=usd
                if a['pay']>day:remaining.append(a)
            adjustments[t]=remaining
        for e in divs[day]:
            if e['ticker'] in refs:
                currency=e['currency'].upper();usd=e['cash_amount']*fx(day,currency)
                refs[e['ticker']][1]-=usd
                if currency!='USD':adjustments.setdefault(e['ticker'],[]).append(dict(face=e['cash_amount'],usd=usd,pay=e['pay_date'],currency=currency))
        pre=dict(shares)
        for t,e in data.cash_actions.items():
            if e['effective_date']==day and t in shares:
                shares.pop(t);refs.pop(t,None);queued.pop(t,None)
        for t,e in data.stock_actions.items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);succ=e['successor_ticker'];ratio=e['shares_per_share'];old=shares.get(succ,0)
                items=adjustments.pop(t,[])
                for a in items:a['face']/=ratio;a['usd']/=ratio
                adjustments.setdefault(succ,[]).extend(items)
                shares[succ]=old+q*ratio
                ref=refs.pop(t,None)
                if ref:
                    converted=[(v-e.get('cash_per_share',0))/ratio for v in ref]
                    if old and succ in refs:
                        converted=[(a*q*ratio+z*old)/(q*ratio+old) for a,z in zip(converted,refs[succ])]
                    refs[succ]=converted
                if t in queued:queued[succ]=queued.pop(t)
        for e in data.distributions:
            if e['ex_date']==day and pre.get(e['parent']):
                t=e['recipient'];shares[t]=shares.get(t,0)+pre[e['parent']]*e['ratio']
        before=dict(shares)
        for tr in by_day[day]:
            t,side,q=tr['ticker'],tr['side'],tr['quantity']
            if side not in ('BUY','SELL'):continue
            assert tr['signal_date']<day
            if side=='BUY':
                assert pending_selection and t in {r['ticker'] for r in pending_selection['targets']}
                assert t not in pending_selection['suppressed']
                assert before.get(t,0)<1,'A continuing whole-share holding was topped up'
                risk=sigma(data,tr['signal_date'],t)
                dist=.10 if s.stop_mode=='fixed10' else 2*risk*math.sqrt(21)
                entry=tr['price'];level=entry*max(0,1-dist)
                if shares.get(t,0) and t in refs:
                    old=shares[t];entry=(refs[t][0]*old+entry*q)/(old+q);level=(refs[t][1]*old+level*q)/(old+q)
                    for a in adjustments.get(t,[]):a['face']*=old/(old+q);a['usd']*=old/(old+q)
                refs[t]=[entry,level];shares[t]=shares.get(t,0)+q
            else:
                reason=tr['reason']
                if reason.startswith('STOP_') or reason=='RISK_OFF':
                    assert t in queued and tr['signal_date']==queued[t][0]
                    assert reason==queued[t][1]
                    if reason.startswith('STOP_'):
                        near(tr['stop_level'],refs[t][1]);near(tr['entry_reference'],refs[t][0]);stop_fills+=1
                    queued.pop(t,None)
                elif reason=='RISK_BUDGET':assert s.risk_budget
                else:
                    assert reason=='MEMBERSHIP_EXIT' and pending_selection
                    active={r['ticker'] for r in pending_selection['targets']}-set(pending_selection['suppressed'])
                    assert t not in active
                shares[t]-=q
                if abs(shares[t])<1e-9:shares.pop(t);refs.pop(t,None)
        if pending_selection and day not in blocked:
            active={r['ticker'] for r in pending_selection['targets']}-set(pending_selection['suppressed'])
            assert all(shares.get(t,0)>=1 for t in active)
            for t in active:
                if before.get(t,0)>=1 and not s.risk_budget:
                    near(shares[t],before[t]);retained_checks+=1
        pending_selection=None
        month=day[:7]
        ordinary=month!=seen and (int(day[5:7])-1)%s.interval==0
        if ordinary:blacklist={}
        locked=set(blacklist)
        c=closes_at(data,day,'SPY',200)
        allowed=c[0]>sum(c)/200
        expected=[]
        if allowed and s.stop_mode!='none':
            for t,q in sorted(shares.items()):
                if q>=1 and t in refs and bars.get(t) and bars[t][1]<=refs[t][1]:
                    expected.append(t)
                    queued.setdefault(t,(day,'STOP_'+s.stop_mode))
                    e=next(e for e in stops[day] if e['ticker']==t)
                    near(e['level'],refs[t][1]);near(e['reference'],refs[t][0]);near(e['close'],bars[t][1])
        assert [e['ticker'] for e in stops[day]]==expected
        assert daily[day]['stops']==expected and daily[day]['risk_on']==allowed and daily[day]['ordinary']==ordinary
        if allowed and (ordinary or not previous_on):
            signal=selections[day]
            near(signal['signal_nav'],next(r['nav'] for r in s.equity if r['date']==day))
            key=(day,s.stage)
            if key not in memo:memo[key]=population(data,day,config,s.stage)
            eligible=[]
            for row in memo[key]:
                t=row['ticker'];p=row['raw_price'];cost=max(1,p*.0025)+p*(.0025+config.one_way_cost)
                if t not in locked and p+cost<=signal['signal_nav']/10:eligible.append(row)
            chosen=independently_choose(eligible,s.stage)
            assert [r['ticker'] for r in signal['targets']]==[r['ticker'] for r in chosen]
            assert signal['eligible_count']==len(eligible) and signal['blacklist']==sorted(locked)
            assert signal['suppressed']==expected
            for a,z in zip(signal['targets'],chosen):
                for field in ('risk_normalized_score','momentum_6m','daily_volatility','score_volatility','return_1m','return_3m','sma63','raw_price','adv20_usd'):near(a[field],z[field])
            if s.risk_budget and chosen:
                series=[closes_at(data,day,r['ticker'],64) for r in chosen]
                x=[sum(c[i]/c[i+1]-1 for c in series)/10 for i in range(63)]
                center=sum(x)/63;vol=math.sqrt(sum((a-center)**2 for a in x)/62*252)
                near(signal['exposure'],min(1,.10/vol) if vol else 1.)
            else:near(signal['exposure'],1.)
            if chosen:pending_selection=signal
            signals+=1
        else:assert day not in selections
        if not allowed:
            for t,q in shares.items():
                if q>=1:queued.setdefault(t,(day,'RISK_OFF'))
        blacklist.update({t:day for t in expected})
        assert daily[day]['blacklist']==sorted(blacklist)
        previous_on,seen=allowed,month
    assert shares.keys()==s.shares.keys()
    for t in shares:near(shares[t],s.shares[t])
    return {'status':'PASS','accounting':account,'benchmark':benchmark,'financial':finance,
            'selection_dates':signals,'retained_quantity_checks':retained_checks,'stop_fills_checked':stop_fills,
            'independent_code':True,'independent_vendor':False}
