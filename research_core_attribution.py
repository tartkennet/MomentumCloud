"""Independent dollar P&L attribution of the exported Core trading ledger."""
import csv
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

from backtest_momentum_v3 import CASH_CORPORATE_ACTIONS, STOCK_CORPORATE_ACTIONS


def read_gzip(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def attribute(cache, results):
    cache, results = Path(cache), Path(results)
    daily = list(csv.DictReader((results / 'Momentum_core_daily.csv').open()))
    trades = defaultdict(list)
    for row in csv.DictReader((results / 'Momentum_core_trades.csv').open()):
        trades[row['date']].append(row)
    splits, dividends = defaultdict(list), defaultdict(list)
    for event in read_gzip(cache / 'splits-2022-06-30-2026-09-01-v1.json.gz'):
        splits[event['execution_date']].append(event)
    for event in read_gzip(cache / 'dividends-2024-01-01-2026-09-01-v1.json.gz'):
        dividends[event['ex_dividend_date']].append(event)
    shares, previous_values, previous_nav = {}, {}, 100000.0
    rows, overall, max_error = [], defaultdict(float), 0.0
    for row in daily:
        day = row['date']
        bars = read_gzip(cache / 'raw-v1' / (day + '.json.gz'))['bars']
        pnl = defaultdict(float, {t: -v for t, v in previous_values.items()})
        for e in splits[day]:
            t = e['ticker']
            if t in shares:
                shares[t] *= e['split_to'] / e['split_from']
        for e in dividends[day]:
            pnl[e['ticker']] += shares.get(e['ticker'], 0) * e['cash_amount']
        for t, e in CASH_CORPORATE_ACTIONS.items():
            if e['effective_date'] == day and t in shares:
                pnl[t] += shares.pop(t) * e['cash_per_share']
        for t, e in STOCK_CORPORATE_ACTIONS.items():
            if e['effective_date'] == day and t in shares:
                q = shares.pop(t) * e['shares_per_share']
                other = e['successor_ticker']
                # A zero-net value transfer allocates overnight conversion
                # P&L to the former ticker, subsequent P&L to its successor.
                value = q * bars[other][1]
                pnl[t] += value
                pnl[other] -= value
                shares[other] = shares.get(other, 0) + q
        for trade in trades[day]:
            t, side = trade['ticker'], trade['side']
            if side not in ('BUY', 'SELL'):
                continue
            q, p, fee = map(float, (trade['quantity'], trade['price'], trade['fee']))
            sign = 1 if side == 'BUY' else -1
            shares[t] = shares.get(t, 0) + sign * q
            pnl[t] -= sign * q * p + fee
            if abs(shares[t]) < 1e-8:
                del shares[t]
        current_values = {t: q * bars[t][1] for t, q in shares.items()}
        for t, value in current_values.items():
            pnl[t] += value
        actual = float(row['nav']) - previous_nav
        error = abs(sum(pnl.values()) - actual)
        assert error < 1e-6, (day, sum(pnl.values()), actual)
        assert math.isclose(sum(current_values.values()), float(row['stock_value']), abs_tol=1e-6)
        max_error = max(max_error, error)
        for t, value in pnl.items():
            if abs(value) > 1e-10:
                rows.append({'date': day, 'ticker': t, 'net_pnl_usd': value})
                overall[t] += value
        previous_values, previous_nav = current_values, float(row['nav'])
    audit = json.loads((results / 'Momentum_core_accounting_audit.json').read_text())
    interval = audit['maximum_drawdown_interval']
    loss = interval['trough_nav_usd'] - interval['peak_nav_usd']
    attribution = defaultdict(float)
    for row in rows:
        if interval['peak_date'] < row['date'] <= interval['trough_date']:
            attribution[row['ticker']] += row['net_pnl_usd']
    assert math.isclose(sum(attribution.values()), loss, abs_tol=1e-6)
    assert math.isclose(sum(overall.values()), previous_nav - 100000, abs_tol=1e-6)
    ranking = lambda values: [{'ticker': t, 'net_pnl_usd': p} for t, p in sorted(values.items(), key=lambda v: v[1])]
    return {'status': 'PASS', 'sessions': len(daily), 'max_daily_pnl_error_usd': max_error,
            'overall_pnl_usd': previous_nav - 100000,
            'overall_attribution': ranking(overall), 'maximum_drawdown_interval': interval,
            'drawdown_loss_usd': loss, 'drawdown_attribution': ranking(attribution),
            'scope': 'Accounting attribution, not an ex-ante security exclusion rule.'}, rows


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache')
    parser.add_argument('results')
    parser.add_argument('output')
    args = parser.parse_args()
    report, rows = attribute(args.cache, args.results)
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'attribution.json').write_text(json.dumps(report, indent=2))
    with (folder / 'daily_attribution.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['date', 'ticker', 'net_pnl_usd'])
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({k: v[:12] if k.endswith('_attribution') else v for k, v in report.items()}, indent=2))
