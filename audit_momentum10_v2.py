"""Independent policy reconstruction. Imports no Momentum10 v2 strategy."""
import copy
import math
from collections import defaultdict
from types import SimpleNamespace
from xml.etree import ElementTree
from datetime import date

from audit_stocks10 import audit as cash_audit, financial_audit, near
from audit_core_normalized import population, closes_at


def independent_fx(data):
    rows={}
    for node in ElementTree.parse(data.fx_xml).iter():
        if 'time' in node.attrib:
            row={c.attrib['currency']:float(c.attrib['rate']) for c in node if 'currency' in c.attrib}
            if 'USD' in row:rows[node.attrib['time']]={'EUR':1.,**row}
    cache={}
    def value(day,currency):
        if currency=='USD':return 1.
        if (day,currency) not in cache:
            prior=sorted(d for d in rows if d<day)[-1]
            assert (date.fromisoformat(day)-date.fromisoformat(prior)).days<=7
            cache[day,currency]=rows[prior]['USD']/rows[prior][currency]
        return cache[day,currency]
    return value


def native_account(data,config,s,fx):
    """Full independent native-currency face claims, fees, raw fills and NAV."""
    by_day=defaultdict(list);split=defaultdict(list);div=defaultdict(list)
    for t in s.trades:by_day[t['date']].append(t)
    for e in data.source.splits:split[e['execution_date']].append(e)
    for e in data.source.dividends:div[e['ex_dividend_date']].append(e)
    cash,fees=config.initial_cash,0.
    shares,claims,payments={},[],[]
    largest,participation=0.,0.
    for row in s.equity:
        day=row['date'];bars=data.bars(day)
        for e in split[day]:
            if e['ticker'] in shares:shares[e['ticker']]*=e['split_to']/e['split_from']
        for e in div[day]:
            t=e['ticker']
            if t in shares:
                assert e.get('pay_date') and e['pay_date']>=day
                claims.append(dict(ticker=t,face=shares[t]*e['cash_amount'],currency=e['currency'].upper(),pay=e['pay_date']))
        live=[]
        for claim in claims:
            if claim['pay'] and claim['pay']<=day:
                gross=claim['face']*fx(day,claim['currency'])
                charge=gross*.0025 if claim['currency']!='USD' else 0.
                cash+=gross-charge;fees+=charge
                if claim['currency']!='USD':payments.append(dict(date=day,ticker=claim['ticker'],gross_usd=gross,fee_usd=charge,native_amount=claim['face']))
            else:live.append(claim)
        claims=live;pre=dict(shares);expected_events=[]
        def add_claim(t,amount,pay):
            nonlocal cash
            if pay and pay<=day:cash+=amount
            else:claims.append(dict(ticker=t,face=amount,currency='USD',pay=pay))
        for t,e in data.cash_actions.items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);add_claim(t,q*e['cash_per_share'],e.get('pay_date'))
                expected_events.append(('CASH_MERGER_CLAIM',t,q,e['cash_per_share']))
        for t,e in data.stock_actions.items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);successor=e['successor_ticker']
                shares[successor]=shares.get(successor,0)+q*e['shares_per_share']
                if e.get('cash_per_share'):
                    add_claim(t,q*e['cash_per_share'],e.get('pay_date'))
                    expected_events.append(('STOCK_MERGER_CASH_CLAIM',t,q,e['cash_per_share']))
        for e in data.distributions:
            q=pre.get(e['parent'],0)*e['ratio']
            if e['ex_date']==day and q:
                shares[e['recipient']]=shares.get(e['recipient'],0)+q
                expected_events.append(('STOCK_DISTRIBUTION',e['recipient'],q,0.))
        actual_events=[]
        for t in by_day[day]:
            symbol,side,q,price=t['ticker'],t['side'],t['quantity'],t['price']
            if side not in ('BUY','SELL'):
                actual_events.append((side,symbol,q,price));continue
            assert symbol!='SPY' and q>0 and float(q).is_integer()
            assert t['signal_date']<day;near(price,bars[symbol][0])
            notional=q*price;charge=max(1,notional*.0025)+notional*(.0025+config.one_way_cost)
            near(t['fee'],charge);fees+=charge
            if side=='BUY':cash-=notional+charge;shares[symbol]=shares.get(symbol,0)+q
            else:
                assert shares.get(symbol,0)+1e-7>=q
                cash+=notional-charge;shares[symbol]-=q
                if abs(shares[symbol])<1e-9:shares.pop(symbol)
            assert cash>=-1e-6
            assert bars[symbol][2]>0
            participation=max(participation,q/bars[symbol][2])
        assert sorted(actual_events)==sorted(expected_events)
        mark=data.halt_marks.get(day)
        def close(t):
            if mark and t==mark['ticker']:
                assert not bars.get(t);return mark['value']
            return bars[t][1]
        stock=sum(q*close(t) for t,q in shares.items())
        due=sum(c['face']*fx(day,c['currency']) for c in claims)
        nav=cash+stock+due;largest=max(largest,abs(nav-row['nav']))
        near(nav,row['nav']);near(cash,row['cash']);near(due,row['receivables']);near(fees,row['fees_cumulative'])
        near(stock,row['stock_value'])
        assert len(shares)==row['positions']
    assert len(payments)==len(s.fx_payments)
    for a,b in zip(payments,s.fx_payments):
        assert a['date']==b['date'] and a['ticker']==b['ticker']
        for key in ('gross_usd','fee_usd','native_amount'):near(a[key],b[key])
    near(cash,s.cash);assert shares.keys()==s.shares.keys()
    for t in shares:near(shares[t],s.shares[t])
    return dict(status='PASS',sessions=len(s.equity),trades=len(s.trades),max_nav_error_usd=largest,
                max_volume_participation=participation,native_currency_payments_checked=len(payments))


def sigma(data, day, t):
    c = closes_at(data,day,t,64)
    x = [c[i]/c[i+1]-1 for i in range(63)]
    mean = sum(x)/63
    return math.sqrt(sum((v-mean)**2 for v in x)/62)


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
            if day not in memo:
                memo[day]=population(data,day,config,formation=True)
                for row in memo[day]:
                    cc=closes_at(data,day,row['ticker'],64)
                    row['_positive_fresh_returns']=cc[0]>cc[21] and cc[0]>cc[63]
            eligible=[]
            for row in memo[day]:
                t=row['ticker'];p=row['raw_price'];cost=max(1,p*.0025)+p*(.0025+config.one_way_cost)
                if t in locked or p+cost>signal['signal_nav']/10:continue
                if row['_positive_fresh_returns']:eligible.append(row)
            chosen=eligible[:10] if len(eligible)>=10 else []
            assert [r['ticker'] for r in signal['targets']]==[r['ticker'] for r in chosen]
            assert signal['eligible_count']==len(eligible) and signal['blacklist']==sorted(locked)
            assert signal['suppressed']==expected
            for a,z in zip(signal['targets'],chosen):near(a['risk_normalized_score'],z['risk_normalized_score'])
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
