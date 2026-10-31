"""Independent reconstruction of the accepted prospective account; no selector imports."""
import math
from datetime import datetime


def near(a,b):
    assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7),(a,b)


def audit_account(state,key,benchmark=False):
    account=state[key];cash=state['initial_usd'];shares={};claims=[];fees=0.;checks=0
    events={e['date']:e for e in state['event_journal']}
    trades={};equity={r['date']:r for r in account['equity']}
    for t in account['trades']:trades.setdefault(t['date'],[]).append(t)
    for day in sorted(set(events)|set(trades)|set(equity)):
        e=events.get(day,dict(splits=[],dividends=[],cash_actions={},stock_actions={},distributions=[],fx={'USD':1}))
        fx=e['fx']
        for r in e['splits']:
            if r['ticker'] in shares:shares[r['ticker']]*=r['split_to']/r['split_from']
        for r in e['dividends']:
            t=r['ticker']
            if shares.get(t):claims.append(dict(ticker=t,face=shares[t]*r['cash_amount'],currency=r['currency'].upper(),pay=r['pay_date']))
        remaining=[]
        for r in claims:
            if r['pay'] and r['pay']<=day:
                amount=r['face']*fx[r['currency']];charge=amount*.0025 if r['currency']!='USD' else 0
                cash+=amount-charge;fees+=charge
            else:remaining.append(r)
        claims=remaining;before=dict(shares);expected=[]
        def claim(t,amount,pay):
            nonlocal cash
            if pay and pay<=day:cash+=amount
            else:claims.append(dict(ticker=t,face=amount,currency='USD',pay=pay))
        for t,r in e['cash_actions'].items():
            if r['effective_date']==day and shares.get(t):
                q=shares.pop(t);claim(t,q*r['cash_per_share'],r.get('pay_date'));expected.append(('CASH_MERGER_CLAIM',t,q,r['cash_per_share']))
                assert not r.get('contingent_cash_per_share'),'Unpriced contingent claim requires review'
        for t,r in e['stock_actions'].items():
            if r['effective_date']==day and shares.get(t):
                q=shares.pop(t);s=r['successor_ticker'];shares[s]=shares.get(s,0)+q*r['shares_per_share']
                if r.get('cash_per_share'):
                    claim(t,q*r['cash_per_share'],r.get('pay_date'));expected.append(('STOCK_MERGER_CASH_CLAIM',t,q,r['cash_per_share']))
        for r in e['distributions']:
            q=before.get(r['parent'],0)*r['ratio']
            if r['ex_date']==day and q:
                t=r['recipient'];shares[t]=shares.get(t,0)+q;expected.append(('STOCK_DISTRIBUTION',t,q,0))
        actual=[]
        for t in trades.get(day,[]):
            symbol,q,price=t['ticker'],t['quantity'],t['price'];side=t['side']
            if side not in ('BUY','SELL'):actual.append((side,symbol,q,price));continue
            assert (symbol=='SPY') if benchmark else symbol!='SPY'
            assert q>0 and float(q).is_integer() and t['signal_date']<day
            decision=next(d for d in state['decisions'] if d['sha256']==t['commitment_sha256'])
            from hashlib import sha256
            import json
            body={k:v for k,v in decision.items() if k!='sha256'}
            assert sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()==decision['sha256']
            assert datetime.fromisoformat(t['decision_at'])<datetime.fromisoformat(t['execution_at'])<=datetime.fromisoformat(t['quote_observed_at'])
            quote=next(o for o in state['opening_quotes'] if o['date']==day)
            near(price,quote['bars'][symbol][0])
            o=decision['benchmark_order'] if benchmark else next(o for o in decision['plan']['orders'] if o['ticker']==symbol and o['side']==side)
            assert q==o['quantity']
            if side=='BUY':assert price<=o['limit']
            n=q*price;charge=max(1,n*.0025)+n*.004;near(charge,t['fee']);fees+=charge
            if side=='BUY':cash-=n+charge;shares[symbol]=shares.get(symbol,0)+q
            else:
                assert shares.get(symbol,0)+1e-8>=q
                cash+=n-charge;shares[symbol]-=q
                if abs(shares[symbol])<1e-9:shares.pop(symbol)
            assert cash>=-1e-7;checks+=1
        assert sorted(actual)==sorted(expected)
        if day in equity:
            r=equity[day];prices=state['valuation_quotes'][day]['prices'];stock=sum(q*prices[t] for t,q in shares.items());due=sum(c['face']*fx[c['currency']] for c in claims)
            for a,b in [(cash,r['cash']),(fees,r['fees_cumulative']),(stock,r['stock_value']),(due,r['receivables']),(cash+stock+due,r['nav'])]:near(a,b)
    near(cash,account['cash']);near(fees,account['fees']);assert set(shares)==set(account['shares'])
    for t,q in shares.items():near(q,account['shares'][t])
    return dict(status='PASS',trades=checks,valuations=len(equity),corporate_event_days=len(events),independent_code=True)
