"""Independent native claims, fees, raw fills and NAV; derived from existing audited book checker."""
import math

from collections import defaultdict
from audit_stocks10 import near

def audit_performance(ledger,metrics):
    values=[r['nav'] for r in ledger.equity];returns=[(b-a)/a for a,b in zip(values,values[1:])]
    mean=sum(returns)/len(returns);variance=sum((r-mean)**2 for r in returns)/(len(returns)-1) if len(returns)>1 else 0
    peak=values[0];dd=0
    for v in values:peak=max(peak,v);dd=min(dd,(v-peak)/peak*100)
    near(metrics['return_pct'],(values[-1]-values[0])/values[0]*100);near(metrics['max_drawdown_pct'],dd)
    if variance:near(metrics['daily_sharpe_zero_rf'],mean/variance**.5*252**.5)
    near(metrics['fees_usd'],ledger.fees)
    return dict(status='PASS',return_drawdown_sharpe_costs=True,independent_code=True)

def native_account(data,config,s,fx,benchmark=False):
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
            assert (symbol=='SPY' if benchmark else symbol!='SPY') and q>0 and float(q).is_integer()
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

