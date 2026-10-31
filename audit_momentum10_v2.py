"""Independent policy reconstruction. Imports no Momentum10 v2 strategy."""
import copy
import math
from collections import defaultdict
from types import SimpleNamespace

from audit_stocks10 import audit as cash_audit, financial_audit, near
from audit_core_normalized import population, closes_at


def sigma(data, day, t):
    c = closes_at(data,day,t,64)
    x = [c[i]/c[i+1]-1 for i in range(63)]
    mean = sum(x)/63
    return math.sqrt(sum((v-mean)**2 for v in x)/62)


def audit(data,config,s,b,metrics,memo):
    # The established independent event/cash verifier is reused, with policy
    # checks below replacing its old top-up/all-target fill assumptions.
    proxy = SimpleNamespace(**vars(s)); proxy.targets=[]
    account = cash_audit(data,config,proxy,benchmark=True)
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
        for e in divs[day]:
            if e['ticker'] in refs:refs[e['ticker']][1]-=e['cash_amount']
        pre=dict(shares)
        for t,e in data.cash_actions.items():
            if e['effective_date']==day and t in shares:
                shares.pop(t);refs.pop(t,None);queued.pop(t,None)
        for t,e in data.stock_actions.items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);succ=e['successor_ticker'];ratio=e['shares_per_share'];old=shares.get(succ,0)
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
            if day not in memo:memo[day]=population(data,day,config,formation=True)
            eligible=[]
            for row in memo[day]:
                t=row['ticker'];p=row['raw_price'];cost=max(1,p*.0025)+p*(.0025+config.one_way_cost)
                if t in locked or p+cost>signal['signal_nav']/10:continue
                cc=closes_at(data,day,t,64)
                if cc[0]>cc[21] and cc[0]>cc[63]:eligible.append(row)
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
