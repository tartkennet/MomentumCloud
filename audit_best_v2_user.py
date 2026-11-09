"""Independent reconstruction of the accepted prospective account; no selector imports."""
import math
from datetime import datetime


def near(a,b):
    assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7),(a,b)


def replay(state,key,seed,benchmark=False):
    account=state[key];cash=seed['cash'];shares=dict(seed['shares']);claims=[];fees=seed['fees'];checks=0
    events={e['date']:e for e in state['event_journal']}
    trades={};equity={r['date']:r for r in account['equity']}
    for t in account['trades']:
        if not t.get('initialization_kind'):trades.setdefault(t['date'],[]).append(t)
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
            assert quote['bars'][symbol][2]>0
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
    expected_claims={};actual_claims={}
    for c in claims:
        k=(c['ticker'],c['currency'],c['pay']);expected_claims[k]=expected_claims.get(k,0)+c['face']
    latest_fx=events[max(events)]['fx'] if events else {'USD':1}
    for c in account['receivables']:
        currency=c.get('currency','USD');face=c.get('native_amount',c['amount']);k=(c['ticker'],currency,c['pay_date'])
        actual_claims[k]=actual_claims.get(k,0)+face
        near(c['amount'],face*latest_fx[currency])
    assert set(expected_claims)==set(actual_claims)
    for k in expected_claims:near(expected_claims[k],actual_claims[k])
    return dict(status='PASS',trades=checks,valuations=len(equity),corporate_event_days=len(events),independent_code=True)



def validate_seed(source):
    assert source['kind']=='HYPOTHETICAL_PAPER_RECONSTRUCTION' and source['initial_sek']==25000
    assert source['trade_day']==source['mark_date']=='2026-11-09'
    rows=source['holdings'];assert len(rows)==len({r['ticker'] for r in rows})==10
    assert all(r['ticker']!='SPY' and type(r['quantity']) is int and r['quantity']>0 and all(math.isfinite(r[k]) and r[k]>0 for k in ('open_usd','mark_usd')) for r in rows)
    assert math.isfinite(source['fx_rate_sek_per_usd']) and source['fx_rate_sek_per_usd']>0


def audit_account(state):
    from decimal import Decimal as D
    from quality_forward import digest
    from audit_best_v2 import audit_execution
    source=state['source_start'];validate_seed(source)
    assert digest(source)==state['source_start_sha256']
    init=[t for t in state['strategy']['trades'] if t.get('initialization_kind')]
    assert len(init)==10 and {t['ticker'] for t in init}=={h['ticker'] for h in source['holdings']}
    cash=D(25000)/D(str(source['fx_rate_sek_per_usd']));fees=D(0);shares={}
    for h in source['holdings']:
        t=next(t for t in init if t['ticker']==h['ticker']);n=D(h['quantity'])*D(str(h['open_usd']))
        charge=max(D(1),n*D('.0025'))+n*D('.004')
        assert t['quantity']==h['quantity'] and t['price']==h['open_usd'] and t['date']=='2026-11-09'
        assert t['initialization_kind']=='SIMULATED_HISTORICAL_INITIALIZATION' and t['execution_at'] is None and t['actual_execution'] is False
        assert t['source_sha256']==digest(source);near(t['fee'],float(charge))
        cash-=n+charge;fees+=charge;shares[h['ticker']]=h['quantity']
    assert cash>=0
    result=replay(state,'strategy',dict(cash=float(cash),fees=float(fees),shares=shares))
    audit_execution(state)
    result.update(initialization_count=10,source_kind='SIMULATED_HISTORICAL_INITIALIZATION')
    return result
