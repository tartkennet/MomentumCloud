"""Check every exported risk trigger and next-session stop fill independently.

Does not import the candidate ledgers, replay or selection code. This checks
the declared price-based risk policy, not alpha or actual market liquidity.
"""
import csv
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path


def read(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def audit(cache, folder):
    cache, folder = Path(cache), Path(folder)
    decision = json.loads((folder / 'Momentum_core_decision.json').read_text())
    model = decision['model']
    if '-entry-stop10-' not in model and '-trailing-stop10-' not in model:
        return {'status': 'NOT_APPLICABLE', 'model': model}
    trailing = '-trailing-stop10-' in model
    final = json.loads((folder / 'Momentum_core_state.json').read_text())
    facts = json.loads((folder / 'experiment_facts.json').read_text())
    by_date, splits = defaultdict(list), defaultdict(list)
    for row in csv.DictReader((folder / 'Momentum_core_trades.csv').open()):
        by_date[row['date']].append(row)
    for e in read(cache / decision['event_cache_files']['splits']):
        splits[e['execution_date']].append(e)
    daily = list(csv.DictReader((folder / 'Momentum_core_daily.csv').open()))
    shares, reference, pending, cooldown, signals = {}, {}, {}, {}, []
    stop_fills = 0
    for row in daily:
        day = row['date']
        bars = read(cache / 'raw-v1' / (day + '.json.gz'))['bars']
        for e in splits[day]:
            t = e['ticker']
            if t in shares:
                ratio = e['split_to'] / e['split_from']
                shares[t] *= ratio
                reference[t] /= ratio
        for t, e in facts['cash_actions'].items():
            if e['effective_date'] == day and t in shares:
                del shares[t], reference[t]
                pending.pop(t, None)
        for t, e in facts['stock_actions'].items():
            if e['effective_date'] == day and t in shares:
                old, basis = shares.pop(t), reference.pop(t)
                new, ratio = e['successor_ticker'], e['shares_per_share']
                existing = shares.get(new, 0)
                reference[new] = (old * basis + existing * reference.get(new, 0)) / (old * ratio + existing)
                shares[new] = old * ratio + existing
                if t in pending:
                    stamp = pending.pop(t)
                    pending[new] = min(stamp, pending.get(new, stamp))
                if t in cooldown:
                    cooldown[new] = max(cooldown.pop(t), cooldown.get(new, ''))
        expected = {(t, math.floor(shares.get(t, 0) + 1e-9), stamp)
                    for t, stamp in pending.items() if math.floor(shares.get(t, 0) + 1e-9)}
        actual = {(t['ticker'], float(t['quantity']), t['signal_date']) for t in by_date[day]
                  if t.get('reason') in ('ENTRY_STOP10', 'TRAILING_STOP10')}
        assert actual == expected, (day, 'stop fills', actual, expected)
        for t, qty, stamp in expected:
            assert stamp < day
        stop_fills += len(actual)
        pending.clear()
        for trade in by_date[day]:
            t, side = trade['ticker'], trade['side']
            if side not in ('BUY', 'SELL'):
                continue
            q, price = float(trade['quantity']), float(trade['price'])
            old = shares.get(t, 0)
            if side == 'SELL':
                assert old + 1e-8 >= q
                shares[t] = old - q
                if abs(shares[t]) < 1e-9:
                    del shares[t], reference[t]
            else:
                assert cooldown.get(t) != trade['signal_date'][:7], (day, 'same-month re-entry', t)
                reference[t] = (max(reference.get(t, price), price) if trailing
                                else (old * reference.get(t, 0) + q * price) / (old + q))
                shares[t] = old + q
        for t in sorted(shares):
            if math.floor(shares[t] + 1e-9) == 0:
                continue
            close = bars[t][1]
            if trailing:
                reference[t] = max(reference[t], close)
            if close <= reference[t] * .9:
                field = 'high_water' if trailing else 'entry_basis'
                signals.append({'signal_date': day, 'ticker': t, 'close': close,
                                field: reference[t], 'threshold_fraction': .1})
                pending[t], cooldown[t] = day, day[:7]
    assert signals == final['stop_signals'], 'Exported signals differ from independent prefix calculation'
    field = 'high_water' if trailing else 'entry_basis'
    assert reference.keys() == final[field].keys()
    for t, value in reference.items():
        assert math.isclose(value, final[field][t], rel_tol=1e-12, abs_tol=1e-9), (t, 'final risk reference')
    assert set(pending) == set(final['stop_pending'])
    report = {'status': 'PASS', 'model': model, 'sessions_checked': len(daily),
              'signals_checked': len(signals), 'next_session_stop_fills_checked': stop_fills,
              'unexecuted_terminal_signals': len(pending),
              'scope': 'Every declared entry/trailing stop, corporate reference transform, cooldown and next-session fill; not alpha/market execution certification.'}
    (folder / 'Momentum_core_stop_policy_audit.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache')
    parser.add_argument('results')
    args = parser.parse_args()
    print(json.dumps(audit(args.cache, args.results), indent=2))
