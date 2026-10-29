"""Attribute SPY core P&L from two already independently audited account exports.

The benchmark has exactly one purchase, unchanged shares and no later trades.
Its daily stock value identifies SPY closes; its residual NAV change identifies
per-share dividend accrual. No strategy replay or price API request is used.
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def attribute(folder):
    root=Path(folder)
    checkpoint=json.loads((root/'checkpoint.json').read_text())
    audit=json.loads((root/'Momentum_core_accounting_audit.json').read_text())
    assert audit['status']=='PASS'
    benchmark,strategy=checkpoint['benchmark'],checkpoint['strategy']
    quantity=benchmark['shares']['SPY']
    assert len(benchmark['trades'])==1 and benchmark['trades'][0]['side']=='BUY'
    assert benchmark['trades'][0]['quantity']==quantity
    assert len(benchmark['equity'])==len(strategy['equity'])
    trades=defaultdict(list)
    for t in strategy['trades']:
        if t['ticker']=='SPY' and t['side'] in ('BUY','SELL'):trades[t['date']].append(t)
    signals={s['date']:s['risk_on'] for s in strategy['targets']}
    interval=audit['maximum_drawdown_interval']
    peak,trough=interval['peak_date'],interval['trough_date']
    shares=0.;previous_close=None;previous_benchmark_nav=None
    overall=episode=0.;risk_on=False;off=days=0;output=[]
    for i,(b,s) in enumerate(zip(benchmark['equity'],strategy['equity'])):
        day=s['date'];assert b['date']==day
        if day in signals:risk_on=signals[day]
        close=b['stock_value']/quantity if i else None
        old=shares;net=fees=0.
        for t in trades[day]:
            signed=t['quantity']*(1 if t['side']=='BUY' else -1)
            shares+=signed;net+=signed*t['price'];fees+=t['fee']
        if i:
            income=(b['nav']-previous_benchmark_nav-quantity*(close-previous_close))/quantity if i>1 else 0.
            pnl=shares*close-(old*previous_close if old else 0)-net-fees+old*income
            overall+=pnl
            if peak<day<=trough:
                episode+=pnl;off+=not risk_on;days+=1
                output.append({'date':day,'core_pnl_usd':pnl,'risk_on_at_close':risk_on})
        else:
            assert shares==0
        previous_close,previous_benchmark_nav=close,b['nav']
    assert math.isclose(shares,strategy['shares'].get('SPY',0),abs_tol=1e-7)
    total=interval['trough_nav_usd']-interval['peak_nav_usd']
    return {'status':'PASS','peak':peak,'trough':trough,'drawdown_core_pnl_usd':episode,
            'drawdown_other_pnl_usd':total-episode,'drawdown_net_pnl_usd':total,
            'risk_off_sessions_in_episode':off,'sessions_in_episode':days,
            'overall_core_pnl_usd':overall,'daily_episode_core_pnl':output,
            'scope':'Exact attribution from audited benchmark mark/dividend accrual and strategy SPY fills. Risk-off-at-close loss is not assumed avoidable at that close; next-open replay remains necessary.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder');p.add_argument('output');a=p.parse_args()
    report=attribute(a.folder);Path(a.output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
