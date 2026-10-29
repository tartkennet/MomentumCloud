"""Read-only position P&L and ex-ante portfolio-risk diagnosis of saved PR 23.

No security exclusion, trading rule, parameter fit or new market API request.
"""
import argparse
import csv
import gzip
import json
import math
import socket
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

from momentum_core import CONFIG, adjusted_history
from momentum_core_data import atomic_json
from run_core_normalized_research import verify_inputs, accounting_audit
from run_core_risk_research import make_data
from research_core_actions import supplement
from research_core_ledger import complete_data


def read(path):
    with gzip.open(path, 'rt') as f:
        return json.load(f)


def concentration(values, nav):
    weights = {t: v / nav for t, v in values.items() if v > 0}
    gross = sum(weights.values())
    hhi = sum((w / gross)**2 for w in weights.values()) if gross else 0
    return {'gross_exposure': gross, 'largest_weight': max(weights.values(), default=0),
            'top_five_weight': sum(sorted(weights.values(), reverse=True)[:5]),
            'effective_stock_count': 1 / hhi if hhi else 0,
            'weights': weights}


def episodes(daily):
    """Non-overlapping peak/recovery episodes, including an unrecovered end."""
    peak = trough = 0
    result = []
    for i in range(1, len(daily)):
        nav = float(daily[i]['nav'])
        if nav >= float(daily[peak]['nav']):
            if trough > peak:
                result.append((peak, trough, i))
            peak = trough = i
        elif nav < float(daily[trough]['nav']):
            trough = i
    if trough > peak:
        result.append((peak, trough, None))
    return sorted(result, key=lambda e: float(daily[e[1]]['nav']) / float(daily[e[0]]['nav']))


def attribute(cache, folder):
    """Reconstruct share inventory independently of the research ledger."""
    cache, folder = Path(cache), Path(folder)
    decision = json.loads((folder/'Momentum_core_decision.json').read_text())
    facts = json.loads((folder/'experiment_facts.json').read_text())
    daily = list(csv.DictReader((folder/'Momentum_core_daily.csv').open()))
    trades, splits, dividends = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in csv.DictReader((folder/'Momentum_core_trades.csv').open()):
        trades[r['date']].append(r)
    for e in read(cache/decision['event_cache_files']['splits']):
        splits[e['execution_date']].append(e)
    for e in read(cache/decision['event_cache_files']['dividends']):
        dividends[e['ex_dividend_date']].append(e)
    shares, prior_values, prior_nav = {}, {}, 100000.
    pnl_rows, inventory, max_error = [], [], 0.
    for row in daily:
        day, nav = row['date'], float(row['nav'])
        bars = read(cache/'raw-v1'/f'{day}.json.gz')['bars']
        mark = facts.get('halt_marks', {}).get(day)
        def close(t):
            return mark['value'] if mark and mark['ticker'] == t else bars[t][1]
        pnl = defaultdict(float, {t: -v for t, v in prior_values.items()})
        for e in splits[day]:
            if e['ticker'] in shares:
                shares[e['ticker']] *= e['split_to']/e['split_from']
        for e in dividends[day]:
            pnl[e['ticker']] += shares.get(e['ticker'], 0) * e['cash_amount']
        original = dict(shares)
        for t, e in facts['cash_actions'].items():
            if e['effective_date'] == day and t in shares:
                pnl[t] += shares.pop(t) * e['cash_per_share']
        for t, e in facts['stock_actions'].items():
            if e['effective_date'] == day and t in shares:
                old = shares.pop(t)
                q, other = old * e['shares_per_share'], e['successor_ticker']
                value = q * close(other)
                pnl[t] += value + old * e.get('cash_per_share', 0)
                pnl[other] -= value
                shares[other] = shares.get(other, 0) + q
        for e in facts.get('distributions', []):
            if e['ex_date'] == day:
                q = original.get(e['parent'], 0) * e['ratio']
                if q:
                    other = e['recipient']; value = q * close(other)
                    pnl[e['parent']] += value
                    pnl[other] -= value
                    shares[other] = shares.get(other, 0) + q
        for trade in trades[day]:
            if trade['side'] not in ('BUY', 'SELL'):
                continue
            t = trade['ticker']
            q, p, fee = (float(trade[k]) for k in ('quantity', 'price', 'fee'))
            direction = 1 if trade['side'] == 'BUY' else -1
            shares[t] = shares.get(t, 0) + direction*q
            pnl[t] -= direction*q*p + fee
            if abs(shares[t]) < 1e-8:
                del shares[t]
        values = {t: q * close(t) for t, q in shares.items()}
        assert math.isclose(sum(values.values()), float(row['stock_value']), abs_tol=1e-6)
        for t, v in values.items():
            pnl[t] += v
        error = abs(math.fsum(pnl.values()) - (nav-prior_nav))
        assert error < 1e-6, (day, error)
        max_error = max(max_error, error)
        pnl_rows.append(dict(pnl))
        inventory.append(dict(date=day, **concentration(values, nav)))
        prior_values, prior_nav = values, nav
    state = json.loads((folder/'Momentum_core_state.json').read_text())
    assert shares.keys() == state['shares'].keys()
    for t, q in shares.items():
        assert math.isclose(q, state['shares'][t], abs_tol=1e-7)
    return daily, pnl_rows, inventory, max_error


def risk_snapshot(data, day, targets):
    names = [r['ticker'] for r in targets]
    def returns(ticker):
        c = adjusted_history(data, day, ticker, CONFIG.vol_returns+1)
        if not c or any(v <= 0 for v in c):
            return None
        return np.array([c[i]/c[i+1]-1 for i in range(CONFIG.vol_returns)])
    sample = [returns(t) for t in names]
    if not names or any(r is None for r in sample):
        return {'date': day, 'status': 'INSUFFICIENT_HISTORY'}
    x = np.array(sample)
    cov = np.cov(x, ddof=1); cov = np.atleast_2d(cov)
    weights = np.array([r['weight'] for r in targets])
    variance = float(weights @ cov @ weights)
    portfolio = weights @ x
    std = np.sqrt(np.diag(cov))
    corr = cov / np.outer(std, std)
    pair_weight = np.outer(weights, weights); np.fill_diagonal(pair_weight, 0)
    contributions = weights * (cov @ weights) / variance if variance else weights*0
    spy = returns('SPY')
    result = {'date': day, 'status': 'PASS', 'annualized_portfolio_vol': math.sqrt(252*variance),
              'annualized_spy_vol': float(np.std(spy, ddof=1)*math.sqrt(252)),
              'weighted_pair_correlation': float((corr*pair_weight).sum()/pair_weight.sum()) if pair_weight.sum() else None,
              'variance_contributions': sorted([{'ticker':t,'weight':float(w),'fraction':float(c)}
                  for t,w,c in zip(names, weights, contributions)], key=lambda r:-r['fraction']),
              'proxy_correlations': {}}
    result['risk_vs_spy'] = result['annualized_portfolio_vol']/result['annualized_spy_vol']
    for proxy in ('SPY','SOXX','XBI','XLK','IWM'):
        r = returns(proxy)
        if r is not None and np.std(r) > 0 and np.std(portfolio)>0:
            result['proxy_correlations'][proxy] = float(np.corrcoef(portfolio, r)[0,1])
    return result


def analyze(data, folder, cache):
    daily, pnl, inventory, error = attribute(cache, folder)
    signals = json.loads((Path(folder)/'Momentum_core_targets.json').read_text())
    risks = [risk_snapshot(data, s['date'], s['targets']) for s in signals if s['risk_on']]
    status = False; regime = {}
    for s in signals:
        regime[s['date']] = s['risk_on']
    regimes = []
    for row in daily:
        status = regime.get(row['date'], status); regimes.append(status)
    report_episodes = []
    for p,t,recovered in episodes(daily)[:8]:
        loss = defaultdict(float)
        for by_ticker in pnl[p+1:t+1]:
            for ticker, v in by_ticker.items(): loss[ticker] += v
        total = float(daily[t]['nav']) - float(daily[p]['nav'])
        assert math.isclose(sum(loss.values()), total, abs_tol=1e-6)
        report_episodes.append({'peak':daily[p]['date'],'trough':daily[t]['date'],
            'recovery':daily[recovered]['date'] if recovered is not None else None,
            'drawdown_pct':100*(float(daily[t]['nav'])/float(daily[p]['nav'])-1),
            'net_loss_usd':total, 'sessions_to_trough':t-p,
            'spy_return_pct':100*(float(daily[t]['spy_nav'])/float(daily[p]['spy_nav'])-1),
            'risk_on_fraction':sum(regimes[p+1:t+1])/(t-p),
            'peak_inventory':inventory[p], 'trough_inventory':inventory[t],
            'max_single_weight':max(r['largest_weight'] for r in inventory[p:t+1]),
            'min_effective_stock_count':min(r['effective_stock_count'] for r in inventory[p:t+1]),
            'attribution': [{'ticker':k, 'pnl_usd':v, 'pct_of_peak_nav':100*v/float(daily[p]['nav'])}
                            for k,v in sorted(loss.items(),key=lambda kv:kv[1])]})
    worst = sorted(range(1,len(daily)),key=lambda i:float(daily[i]['nav'])/float(daily[i-1]['nav']))[:15]
    records = data.universe(signals[0]['date'])
    report = {'status':'PASS','sessions':len(daily),'max_daily_pnl_error_usd':error,
              'episodes':report_episodes, 'signal_risk':risks,
              'worst_days':[{'date':daily[i]['date'],'return_pct':100*(float(daily[i]['nav'])/float(daily[i-1]['nav'])-1),
                 'positions':sorted(pnl[i].items(),key=lambda kv:kv[1])[:8]} for i in worst],
              'universe_fields':sorted(set().union(*(r.keys() for r in records))),
              'sector_limitation':'ETF correlations are sector-risk proxies, not historical industry classifications. Missing PIT sector fields are not invented.',
              'risk_convention':'63 past split-adjusted simple close returns incl. signal close; no future return; 252 annualization; no shrinkage or fitted window.',
              'evidence_class':'PREVIOUSLY_INSPECTED_DEVELOPMENT','live_approved':False,'broker_orders_enabled':False}
    return report, inventory


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache','manifest','reference','output'): p.add_argument('--'+n,required=True)
    args=p.parse_args(); root=Path(args.output); root.mkdir(parents=True,exist_ok=True)
    def blocked(*a,**kw): raise RuntimeError('No network allowed in saved-data diagnosis')
    socket.socket.connect=blocked; socket.create_connection=blocked
    before=verify_inputs(args.cache,args.manifest)
    folder=Path(args.reference)/'extension/formation_assumed_5_15bps_last_quote'
    assert accounting_audit(args.cache,folder)['status']=='PASS'
    data=complete_data(supplement(make_data(args.cache,'2026-10-28',True)))
    report,inventory=analyze(data,folder,args.cache)
    assert before==verify_inputs(args.cache,args.manifest)
    report['input_manifest_fingerprint']=before
    atomic_json(root/'risk_diagnosis.json',report)
    atomic_json(root/'daily_inventory.json',inventory)
    lines=['# PR 23 portfolio risk diagnosis', '',
           'Previously inspected development evidence. No new trading rule or financial approval.', '',
           '| Peak | Trough | Drawdown % | SPY % | Risk-on fraction | Max stock weight | Min effective stocks |',
           '|---|---|---:|---:|---:|---:|---:|']
    for e in report['episodes']:
        lines.append(f"| {e['peak']} | {e['trough']} | {e['drawdown_pct']:.3f} | {e['spy_return_pct']:.3f} | {e['risk_on_fraction']:.3f} | {e['max_single_weight']:.3f} | {e['min_effective_stock_count']:.2f} |")
    for e in report['episodes']:
        lines += ['', f"## {e['peak']} to {e['trough']}"]
        lines += ['', 'Largest net P&L contributions in this episode: '+', '.join(f"{r['ticker']} {r['pnl_usd']:.2f} USD" for r in e['attribution'][:8]), '']
    lines += ['', 'Signal covariance, variance contributions and sector-proxy correlations are preserved in JSON.',
              report['sector_limitation'], f"Daily P&L reconciliation max error: {report['max_daily_pnl_error_usd']} USD."]
    (root/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('signal_risk','episodes')},indent=2))
    for e in report['episodes']:
        print('EPISODE',json.dumps({k:v[:10] if k=='attribution' else v for k,v in e.items() if k not in ('peak_inventory','trough_inventory')}))


if __name__=='__main__': main()
