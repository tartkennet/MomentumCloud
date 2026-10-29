"""Independent H1 variance/weight/timing audit; imports no candidate module."""
import math
from audit_core_normalized import closes_at, expected_weights, near


def expected_risk(data, day, rows, config):
    returns = {}
    for name in [r['ticker'] for r in rows]+['SPY']:
        closes = closes_at(data, day, name, config.vol_returns+1)
        assert len(closes)==config.vol_returns+1
        x=[closes[i]/closes[i+1]-1 for i in range(config.vol_returns)]
        mean=math.fsum(x)/len(x)
        returns[name]=[r-mean for r in x]
    w=expected_weights(rows,config)
    # w' Sigma w, independently of the candidate's weighted-return stdev.
    var=math.fsum(w[a]*w[b]*math.fsum(x*y for x,y in zip(returns[a],returns[b]))/(config.vol_returns-1)
                  for a in w for b in w)
    spy_var=math.fsum(r*r for r in returns['SPY'])/(config.vol_returns-1)
    assert var>0 and spy_var>0
    scale=min(1.,math.sqrt(spy_var/var))
    return w,scale,math.sqrt(var),math.sqrt(spy_var)


def audit_targets(data, config, targets, reference_signals, trades=(), memo=None):
    memo={} if memo is None else memo
    previous,month=False,''; expected=[]
    for i,day in enumerate(data.sessions):
        key=('portfolio-regime',day)
        if key not in memo:
            c=closes_at(data,day,'SPY',200)
            assert len(c)==200
            memo[key]=c[0]>math.fsum(c)/200
        allowed=memo[key]
        if allowed and (month!=day[:7] or not previous):
            expected.append((day,True)); month=day[:7]
        elif not allowed and (previous or i==0): expected.append((day,False))
        previous=allowed
    assert [(s['date'],s['risk_on']) for s in targets]==expected
    count=0
    for signal in targets:
        ref=reference_signals[signal['date']]
        assert signal['risk_on']==ref['risk_on'] and signal['eligible_count']==ref['eligible_count']
        if not signal['risk_on']:
            assert not signal['targets']; continue
        rows=ref['targets']
        assert [r['ticker'] for r in signal['targets']]==[r['ticker'] for r in rows]
        key=('independent-portfolio-variance',signal['date'])
        if key not in memo: memo[key]=expected_risk(data,signal['date'],rows,config)
        weights,scale,pvol,svol=memo[key]
        for actual,original in zip(signal['targets'],rows):
            for field,value in original.items():
                if field not in ('ticker','weight'): near(actual[field],value,field)
            near(actual['weight'],weights[original['ticker']]*scale,'portfolio weight')
            near(actual['portfolio_risk_scale'],scale,'risk scale')
            near(actual['portfolio_vol63'],pvol,'aggregate covariance risk')
            near(actual['benchmark_vol63'],svol,'benchmark risk')
        assert sum(r['weight'] for r in signal['targets'])<=1.+1e-10
        count+=len(rows)
    next_day=dict(zip(data.sessions,data.sessions[1:])); fills=0
    for t in trades:
        if t['side'] in ('BUY','SELL','BUY_CANCELLED_NO_OPEN'):
            assert next_day.get(t['signal_date'])==t['date']; fills+=1
    return {'status':'PASS','signals_checked':len(targets),'selected_rows_checked':count,
            'base_ranking':'Unchanged from hash-verified independently audited PR23 selections',
            'next_session_orders_checked':fills,
            'scope':'Independent covariance algebra, original inverse-risk proportions, risk scaling, dates and fills; common immutable vendor data.'}
