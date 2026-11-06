"""Independent exported SEK account checks, separate from the Avanza renderer."""
import math
from datetime import datetime


def check(state, report):
    def near(a,b):
        assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-6),(a,b)
    account=state['strategy']
    assert report['live_approved'] is False and report['broker_orders_enabled'] is False
    assert report['paper_started'] is bool(account['trades'])
    assert all(t['ticker']!='SPY' for t in account['trades'])
    assert len({r['date'] for r in report['curve']})==len(report['curve'])
    assert len(report['curve'])==len(account['equity'])
    config=state.get('capital_configuration')
    if config:
        assert config['initial_sek']==state['initial_sek']
        from quality_forward import digest
        assert state['cohort_id']==digest(config)
        if config['mode']=='AUTO_MINIMUM':assert config['initial_sek']==config['funding']['minimum_capital_sek']
    initial=state['initial_sek'];peak=initial;drawdown=0
    for mark, row in zip(account['equity'], report['curve']):
        assert mark['date']==row['date']
        assert state['valuation_fx'][row['date']]['date']<=row['date']
        rate=state['valuation_fx'][row['date']]['usdsek']
        near(row['nav_sek'],mark['nav']*rate)
        assert datetime.fromisoformat(row['observed_at'])>=datetime.fromisoformat(state['initialized_at'])
        peak=max(peak,row['nav_sek']);drawdown=min(drawdown,(row['nav_sek']/peak-1)*100)
    near(report['drawdown_pct'],drawdown)
    if report['valuation_pending']:
        assert report['nav_sek'] is None and report['return_sek'] is None
    else:
        value=report['curve'][-1]['nav_sek'] if report['curve'] else initial
        near(report['nav_sek'],value);near(report['return_sek'],value-initial)
        near(report['return_pct'],100*(value/initial-1))
        if report['curve']:
            shares_value=sum(r['value_sek'] for r in report['positions'])
            claims=account['equity'][-1]['receivables']*report['curve'][-1]['usdsek']
            near(value,report['cash_sek']+shares_value+claims)
    costs=0
    for t in account['trades']:
        if t['side'] not in ('BUY','SELL'):continue
        assert datetime.fromisoformat(t['execution_at'])>datetime.fromisoformat(state['initialized_at'])
        rate=state['trade_fx'][t['date']]
        assert rate['date']<=t['date']
        costs+=t['fee']*rate['usdsek']
    near(report['costs_sek'],costs)
    assert {p['ticker']:p['quantity'] for p in report['positions']}==account['shares']
    if report['status']=='MONITORING' and report['risk_on']:
        assert len(account['shares'])==10
    return dict(status='PASS',independent_code=True,valuations=len(report['curve']),trades=len(account['trades']))


def audit_funding(snapshot, fx, funding):
    """Independent Decimal reconciliation of selected names, costs and caps."""
    from decimal import Decimal, ROUND_CEILING
    selected=[];issuers=set()
    for row in snapshot['selection']['rows']:
        sector=row['division'];industry=str(row['sic'])[:2]
        if row['ticker']=='SPY' or row['cik'] in issuers:continue
        if sum(str(r['sic'])[:2]==industry for r in selected)>=2:continue
        if sum(r['division']==sector for r in selected)>=4:continue
        selected.append(row);issuers.add(row['cik'])
        if len(selected)==10:break
    assert len(selected)==10
    assert [r['ticker'] for r in selected]==[r['ticker'] for r in funding['targets']]
    charges=[]
    for row,out in zip(selected,funding['targets']):
        price=Decimal(str(snapshot['quotes'][row['ticker']]))
        notional=price*Decimal('1.02')
        exact=(notional+max(Decimal(1),notional*Decimal('.0025'))+notional*Decimal('.004'))*Decimal(str(fx))*100
        cents=int(exact.to_integral_value(rounding=ROUND_CEILING))
        # Floating point conservative round-up may add a cent, never lose one.
        assert cents<=out['one_share_cost_cents']<=cents+1
        charges.append(out['one_share_cost_cents'])
    total=sum(charges)
    required=Decimal(total)
    for row,cost in zip(selected,charges):
        required=max(required,Decimal(cost)/Decimal('.20'),
            sum(Decimal(c) for r,c in zip(selected,charges) if str(r['sic'])[:2]==str(row['sic'])[:2])/Decimal('.30'),
            sum(Decimal(c) for r,c in zip(selected,charges) if r['division']==row['division'])/Decimal('.50'))
    assert funding['minimum_one_each_sek']==total/100
    assert funding['minimum_capital_sek']==int(required.to_integral_value(rounding=ROUND_CEILING))/100
    return dict(status='PASS',independent_code=True,stocks=10)
