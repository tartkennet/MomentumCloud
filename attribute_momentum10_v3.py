"""Read completed v2 states: independent P&L attribution, never strategy replay."""
import argparse
import copy
import json
import socket
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import momentum_core as core
from audit_momentum10_v2 import independent_fx
from audit_stocks10 import near
from audit_core_normalized import closes_at
from research_core_actions import supplement
from research_core_ledger import complete_data
from research_stocks10 import APGE_COMPLETION
from research_momentum10_fx import supplement_native_dividend
from run_core_normalized_research import verify_inputs,payment_policy
from run_core_risk_research import make_data,EXTENSION_END
from momentum_core_data import atomic_json

def attribute_account(data,config,s,fx):
    """Full independent native-currency face claims, fees, raw fills and NAV."""
    by_day=defaultdict(list);split=defaultdict(list);div=defaultdict(list)
    for t in s.trades:by_day[t['date']].append(t)
    for e in data.source.splits:split[e['execution_date']].append(e)
    for e in data.source.dividends:div[e['ex_dividend_date']].append(e)
    previous_assets={};previous_nav=config.initial_cash;daily=[]
    cash,fees=config.initial_cash,0.
    shares,claims,payments={},[],[]
    largest,participation=0.,0.
    for row in s.equity:
        day=row['date'];bars=data.bars(day);flows=defaultdict(float)
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
                cash+=gross-charge;fees+=charge;flows[claim['ticker']]+=gross-charge
                if claim['currency']!='USD':payments.append(dict(date=day,ticker=claim['ticker'],gross_usd=gross,fee_usd=charge,native_amount=claim['face']))
            else:live.append(claim)
        claims=live;pre=dict(shares);expected_events=[]
        def add_claim(t,amount,pay):
            nonlocal cash
            if pay and pay<=day:
                cash+=amount;flows[t]+=amount
            else:claims.append(dict(ticker=t,face=amount,currency='USD',pay=pay))
        for t,e in data.cash_actions.items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);add_claim(t,q*e['cash_per_share'],e.get('pay_date'))
                expected_events.append(('CASH_MERGER_CLAIM',t,q,e['cash_per_share']))
        for t,e in data.stock_actions.items():
            if e['effective_date']==day and t in shares:
                q=shares.pop(t);successor=e['successor_ticker']
                shares[successor]=shares.get(successor,0)+q*e['shares_per_share']
                transfer=q*e['shares_per_share']*bars[successor][1]
                flows[t]+=transfer;flows[successor]-=transfer
                if e.get('cash_per_share'):
                    add_claim(t,q*e['cash_per_share'],e.get('pay_date'))
                    expected_events.append(('STOCK_MERGER_CASH_CLAIM',t,q,e['cash_per_share']))
        for e in data.distributions:
            q=pre.get(e['parent'],0)*e['ratio']
            if e['ex_date']==day and q:
                shares[e['recipient']]=shares.get(e['recipient'],0)+q
                transfer=q*bars[e['recipient']][1]
                flows[e['parent']]+=transfer;flows[e['recipient']]-=transfer
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
            if side=='BUY':
                cash-=notional+charge;shares[symbol]=shares.get(symbol,0)+q;flows[symbol]-=notional+charge
            else:
                assert shares.get(symbol,0)+1e-7>=q
                cash+=notional-charge;shares[symbol]-=q;flows[symbol]+=notional-charge
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
        assets={t:q*close(t) for t,q in shares.items()}
        for claim in claims:assets[claim['ticker']]=assets.get(claim['ticker'],0)+claim['face']*fx(day,claim['currency'])
        contributions={t:assets.get(t,0)-previous_assets.get(t,0)+flows[t] for t in set(assets)|set(previous_assets)|set(flows)}
        near(sum(contributions.values()),nav-previous_nav)
        weights={t:q*close(t)/nav for t,q in shares.items()}
        trend=[];unknown=[]
        for t in shares:
            c=closes_at(data,day,t,63)
            if len(c)!=63:unknown.append(t)
            elif c[0]<=sum(c)/63:trend.append(t)
        daily.append(dict(date=day,nav=nav,pnl_by_ticker=contributions,weights=weights,
            held_below_sma63=trend,missing_trend_history=unknown))
        previous_assets=assets;previous_nav=nav
    assert len(payments)==len(s.fx_payments)
    for a,b in zip(payments,s.fx_payments):
        assert a['date']==b['date'] and a['ticker']==b['ticker']
        for key in ('gross_usd','fee_usd','native_amount'):near(a[key],b[key])
    near(cash,s.cash);assert shares.keys()==s.shares.keys()
    for t in shares:near(shares[t],s.shares[t])
    peak=s.equity[0];worst=0.;episode=(peak,peak)
    for row in s.equity:
        if row['nav']>peak['nav']:peak=row
        dd=row['nav']/peak['nav']-1
        if dd<worst:worst=dd;episode=(peak,row)
    start,end=episode;contributions=defaultdict(float);held=0;below=0;missing=0
    for row in daily:
        if not start['date']<row['date']<=end['date']:continue
        for t,pnl in row['pnl_by_ticker'].items():contributions[t]+=pnl
        held+=len(row['weights']);below+=len(row['held_below_sma63']);missing+=len(row['missing_trend_history'])
    near(sum(contributions.values()),end['nav']-start['nav'])
    return dict(status='PASS',largest_nav_residual_usd=largest,
        episode=dict(peak=start['date'],trough=end['date'],peak_nav=start['nav'],trough_nav=end['nav'],
            drawdown_pct=worst*100,net_pnl_usd=end['nav']-start['nav']),
        drawdown_contribution_usd=sorted(contributions.items(),key=lambda a:a[1]),
        held_stock_days=held,held_below_sma63_stock_days=below,missing_trend_stock_days=missing,
        below_sma63_fraction=below/(held-missing) if held>missing else None,
        max_single_weight_pct=max((max(r['weights'].values(),default=0)*100 for r in daily),default=0),
        daily=daily,
        convention='Independent cash/claims/position reconstruction; includes fees and dividend/native-FX effects. Stock exchanges/spins allocate value transfers at same-day observed successor close solely for attribution, never as a trade. All daily ticker P&L sums reconcile exactly to NAV changes.')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cache','manifest','v2','output'):p.add_argument('--'+name,required=True)
    args=p.parse_args()
    def offline(*a,**kw):raise RuntimeError('No network in saved-state attribution')
    socket.socket.connect=offline;socket.create_connection=offline
    manifest=verify_inputs(args.cache,args.manifest)
    data=complete_data(supplement(make_data(args.cache,EXTENSION_END,True)))
    data.source.cash_actions['APGE']=copy.deepcopy(APGE_COMPLETION)
    data.fx_xml=Path(args.v2)/'ecb-history.xml';supplement_native_dividend(data)
    complete_data(data,'last_quote');payment_policy(data,5)
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    result=dict(status='RUNNING',input_manifest=manifest,baseline_only=True,strategy_replay=False,variants={})
    for v in ('M1','M3','Q10'):
        state=json.loads((Path(args.v2)/f'{v}_5_last_quote_15/strategy.json').read_text())
        s=SimpleNamespace(**state);initial=s.equity[0]['nav']
        a=attribute_account(data,replace(core.CONFIG,initial_cash=initial,positions=10),s,independent_fx(data))
        daily=a.pop('daily');atomic_json(root/(v+'_daily.json'),daily)
        result['variants'][v]=a;atomic_json(root/'attribution.json',result)
        print(v,json.dumps(a),flush=True)
    result['status']='PASS';atomic_json(root/'attribution.json',result)
