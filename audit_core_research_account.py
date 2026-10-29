"""Independent reconciliation of Core exports; no replay/ledger/metric calls."""
import csv
import gzip
import json
import math
from pathlib import Path
import sys
from collections import defaultdict

from backtest_momentum_v3 import CASH_CORPORATE_ACTIONS, STOCK_CORPORATE_ACTIONS

cache, results = map(Path, sys.argv[1:3])
def read(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)
def near(a, b, label):
    if not math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-6):
        raise AssertionError(f'{label}: {a} != {b}')

decision = json.loads((results / 'Momentum_core_decision.json').read_text())
cost = decision['config']['one_way_cost']
facts = json.loads((results / 'experiment_facts.json').read_text())
CASH_CORPORATE_ACTIONS = facts['cash_actions']
STOCK_CORPORATE_ACTIONS = facts['stock_actions']
with (results / 'Momentum_core_daily.csv').open() as stream:
    daily = list(csv.DictReader(stream))
with (results / 'Momentum_core_trades.csv').open() as stream:
    trades = list(csv.DictReader(stream))
by_date = defaultdict(list)
for row in trades:
    by_date[row['date']].append(row)
events = defaultdict(list)
for e in read(cache / decision['event_cache_files']['splits']):
    events[e['execution_date']].append(('split', e))
for e in read(cache / decision['event_cache_files']['dividends']):
    events[e['ex_dividend_date']].append(('dividend', e))
cash, fees, notional = 100000.0, 0.0, 0.0
shares, claims = {}, []
spy_cash, spy_shares, spy_claims = 100000.0, 0, []
peak, drawdown, max_error = 100000.0, 0.0, 0.0
peak_date, drawdown_dates = daily[0]['date'], None
max_participation, max_weight = 0.0, 0.0
for index, row in enumerate(daily):
    day = row['date']
    bars = read(cache / 'raw-v1' / f'{day}.json.gz')['bars']
    for kind, e in events[day]:
        t = e['ticker']
        if kind == 'split':
            if t in shares:
                shares[t] *= e['split_to'] / e['split_from']
            if t == 'SPY':
                spy_shares *= e['split_to'] / e['split_from']
    for kind, e in events[day]:
        t = e['ticker']
        if kind == 'dividend':
            if t in shares:
                claims.append((shares[t] * e['cash_amount'], e['pay_date']))
            if t == 'SPY' and spy_shares:
                spy_claims.append((spy_shares * e['cash_amount'], e['pay_date']))
    cash += sum(a for a, d in claims if d and d <= day)
    claims = [(a, d) for a, d in claims if not d or d > day]
    spy_cash += sum(a for a, d in spy_claims if d and d <= day)
    spy_claims = [(a, d) for a, d in spy_claims if not d or d > day]
    merger_rows = []
    mixed_rows, distribution_rows = [], []
    before_mergers = dict(shares)
    for t, e in CASH_CORPORATE_ACTIONS.items():
        if e['effective_date'] == day and t in shares:
            q = shares.pop(t)
            amount = q * e['cash_per_share']
            if e.get('pay_date') and e['pay_date'] <= day:
                cash += amount
            else:
                claims.append((amount, e.get('pay_date')))
            merger_rows.append((t, q, e['cash_per_share']))
    for t, e in STOCK_CORPORATE_ACTIONS.items():
        if e['effective_date'] == day and t in shares:
            original_qty = shares.pop(t)
            if e.get('cash_per_share'):
                amount = original_qty * e['cash_per_share']
                if e.get('pay_date') and e['pay_date'] <= day:
                    cash += amount
                else:
                    claims.append((amount, e.get('pay_date')))
                mixed_rows.append((t, original_qty, e['cash_per_share']))
            q = original_qty * e['shares_per_share']
            successor = e['successor_ticker']
            shares[successor] = shares.get(successor, 0) + q
    for e in facts.get('distributions', []):
        if e['ex_date'] == day:
            q = before_mergers.get(e['parent'], 0) * e['ratio']
            if q:
                shares[e['recipient']] = shares.get(e['recipient'], 0) + q
                distribution_rows.append((e['recipient'], q, e['parent']))
    actual_mergers, actual_mixed, actual_distributions = [], [], []
    for trade in by_date[day]:
        t, side = trade['ticker'], trade['side']
        q, fee = float(trade['quantity']), float(trade['fee'])
        if side == 'BUY_CANCELLED_NO_OPEN':
            assert q == 0 and fee == 0
            continue
        price = float(trade['price'])
        if side == 'STOCK_DISTRIBUTION':
            assert fee == 0 and price == 0
            actual_distributions.append((t, q, trade['parent']))
            continue
        if side == 'STOCK_MERGER_CASH_CLAIM':
            assert fee == 0
            actual_mixed.append((t, q, price))
            continue
        if side == 'CASH_MERGER_CLAIM':
            actual_mergers.append((t, q, price))
            continue
        assert side in ('BUY', 'SELL') and q > 0 and q.is_integer()
        assert trade['signal_date'] < day
        near(price, bars[t][0], f'{day} {t} open')
        near(fee, q * price * cost, f'{day} {t} fee')
        notional += q * price
        if bars[t][2] > 0:
            max_participation = max(max_participation, q / bars[t][2])
        fees += fee
        if side == 'BUY':
            cash -= q * price + fee
            shares[t] = shares.get(t, 0) + q
        else:
            assert shares.get(t, 0) + 1e-7 >= q
            cash += q * price - fee
            shares[t] -= q
            if abs(shares[t]) < 1e-9:
                del shares[t]
        assert cash >= -1e-6
    assert sorted(merger_rows) == sorted(actual_mergers)
    assert sorted(mixed_rows) == sorted(actual_mixed)
    assert sorted(distribution_rows) == sorted(actual_distributions)
    if index == 1:
        price = bars['SPY'][0]
        wanted = math.floor(100000 / price)
        spy_shares = math.floor(wanted * min(1, 100000 / (wanted * price * (1 + cost))) + 1e-10)
        spy_cash -= spy_shares * price * (1 + cost)
    mark = facts.get('halt_marks', {}).get(day)
    def valuation(t):
        if mark and t == mark['ticker']:
            assert not bars.get(t), 'A halt valuation must not replace an observed quote'
            if mark['policy'] == 'last_quote':
                actual = read(cache / 'raw-v1' / (mark['last_session'] + '.json.gz'))['bars'][t][1]
            else:
                assert mark['policy'] == 'offer_value'
                actual = mark['offer_value']
            near(mark['value'], actual, 'Suspension valuation policy')
            return actual
        return bars[t][1]
    stock = sum(q * valuation(t) for t, q in shares.items())
    receivables = sum(a for a, d in claims)
    nav = cash + stock + receivables
    spy_nav = spy_cash + spy_shares * bars['SPY'][1] + sum(a for a, d in spy_claims)
    for key, value in [('cash', cash), ('stock_value', stock), ('receivables', receivables),
                       ('nav', nav), ('fees_cumulative', fees), ('spy_nav', spy_nav), ('positions', len(shares))]:
        near(row[key], value, f'{day} {key}')
    max_error = max(max_error, abs(float(row['nav']) - nav))
    max_weight = max(max_weight, max((q * valuation(t) / nav for t, q in shares.items()), default=0))
    if nav >= peak:
        peak, peak_date = nav, day
    current_dd = 100 * (nav / peak - 1)
    if current_dd < drawdown:
        drawdown = current_dd
        drawdown_dates = {'peak_date': peak_date, 'trough_date': day, 'peak_nav_usd': peak, 'trough_nav_usd': nav}
boundaries = [r for i, r in enumerate(daily) if i == 0 or r['date'][:7] != daily[i - 1]['date'][:7]]
returns = [100 * (float(b['nav']) / float(a['nav']) - 1) for a, b in zip(boundaries, boundaries[1:])]
checks = {'Periods': len(returns), 'TotalReturn_pct': 100 * (nav / 100000 - 1),
          'SPYTotalReturn_pct': 100 * (spy_nav / 100000 - 1), 'DailyMaxDrawdown_pct': drawdown,
          'PeriodHitRate_pct': 100 * sum(r > 0 for r in returns) / len(returns),
          'ActualFees_USD': fees, 'FinalNAV_USD': nav}
checks['TotalEdgeVsSPY_pct'] = checks['TotalReturn_pct'] - checks['SPYTotalReturn_pct']
for key, value in checks.items():
    near(value, decision['metrics'][key], key)
if 'DailySharpe_zero_rf' in decision['metrics']:
    daily_returns = [float(b['nav']) / float(a['nav']) - 1 for a, b in zip(daily, daily[1:])]
    mean = math.fsum(daily_returns) / len(daily_returns)
    sigma = math.sqrt(math.fsum((r - mean)**2 for r in daily_returns) / (len(daily_returns) - 1))
    if sigma:
        near(math.sqrt(252) * mean / sigma, decision['metrics']['DailySharpe_zero_rf'], 'Independent Sharpe')
    else:
        assert decision['metrics']['DailySharpe_zero_rf'] is None
state = json.loads((results / 'Momentum_core_state.json').read_text())
assert shares.keys() == state['shares'].keys()
for t, q in shares.items():
    near(q, state['shares'][t], f'Final shares {t}')
report = {'status': 'PASS', 'sessions_reconciled': len(daily), 'trade_rows_checked': len(trades),
          'max_nav_error_usd': max_error, 'metrics_recomputed': checks, 'traded_notional_usd': notional,
          'max_trade_fraction_of_full_day_volume': max_participation, 'max_observed_stock_weight': max_weight,
          'maximum_drawdown_interval': drawdown_dates, 'positive_months': sum(r > 0 for r in returns),
          'final_unsettled_fixed_claims_usd': sum(a for a, d in claims if not d),
          'scope': 'Independent cash/share/mixed-consideration/distribution/halt-mark/fill/fee/NAV/SPY/metrics audit; not independent vendor or alpha evidence.'}
(results / 'Momentum_core_accounting_audit.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
