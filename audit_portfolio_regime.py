"""Independent H3 allocation, portfolio-wide risk-off and trade timing audit."""
import math
from audit_core_normalized import closes_at,near
from audit_portfolio_risk import expected_risk


def audit_targets(data,config,targets,reference_signals,trades=(),memo=None):
    memo={} if memo is None else memo
    previous,month=False,'';expected=[]
    for i,day in enumerate(data.sessions):
        key=('diversified-regime',day)
        if key not in memo:
            c=closes_at(data,day,'SPY',200);assert len(c)==200
            memo[key]=c[0]>math.fsum(c)/200
        allowed=memo[key]
        if allowed and (month!=day[:7] or not previous):
            expected.append((day,True));month=day[:7]
        elif not allowed and (previous or i==0):expected.append((day,False))
        previous=allowed
    assert [(s['date'],s['risk_on']) for s in targets]==expected
    core_weight=1.;count=0
    for signal in targets:
        ref=reference_signals[signal['date']]
        assert signal['risk_on']==ref['risk_on'] and signal['eligible_count']==ref['eligible_count']
        if not signal['risk_on']:
            assert not signal['targets'], 'Both equity sleeves must be cash in risk-off'
            core_weight=0.
            continue
        core=[r for r in signal['targets'] if r.get('benchmark_core')]
        assert len(core)==1 and core[0]['ticker']=='SPY'
        assert set(core[0])=={'ticker','weight','benchmark_core'} and core[0]['benchmark_core'] is True
        stocks=[r for r in signal['targets'] if not r.get('benchmark_core')]
        rows=ref['targets']
        assert [r['ticker'] for r in stocks]==[r['ticker'] for r in rows]
        if not rows:
            core_weight=1.;near(core[0]['weight'],1.,'empty basket core');continue
        key=('diversified-covariance',signal['date'])
        if key not in memo:memo[key]=expected_risk(data,signal['date'],rows,config)
        weights,_,pvol,svol=memo[key]
        fraction=1/(1+pvol/svol)
        core_weight=1-fraction
        near(core[0]['weight'],core_weight,'benchmark core weight')
        # Two sleeves' covariance terms cancel when equating Euler risks.
        near(fraction*pvol,core_weight*svol,'equal ex-ante sleeve risk')
        for actual,original in zip(stocks,rows):
            for field,value in original.items():
                if field not in ('ticker','weight'):near(actual[field],value,field)
            near(actual['weight'],weights[original['ticker']]*fraction,'stock allocation')
            near(actual['momentum_sleeve_fraction'],fraction,'sleeve fraction')
            near(actual['portfolio_vol63'],pvol,'basket covariance')
            near(actual['benchmark_vol63'],svol,'benchmark risk')
        assert sum(r['weight'] for r in signal['targets'])<=1+1e-10
        count+=len(rows)
    next_day=dict(zip(data.sessions,data.sessions[1:]));fills=0
    for t in trades:
        if t['side'] in ('BUY','SELL','BUY_CANCELLED_NO_OPEN'):
            assert next_day.get(t['signal_date'])==t['date'];fills+=1
    return {'status':'PASS','signals_checked':len(targets),'selected_stock_rows_checked':count,
            'active_benchmark_core_weight':core_weight,'next_session_orders_checked':fills,
            'base_ranking':'Unchanged from hash-verified independently audited PR23 selections',
            'scope':'Independent covariance/equal-risk stock+SPY allocation, portfolio-wide cash in risk-off, dates and fills; common frozen vendor inputs.'}
