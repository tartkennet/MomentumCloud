"""Independent arithmetic and eligible-universe reconstruction. No candidate import."""
import math
from collections import defaultdict
from dataclasses import replace

from audit_core_normalized import population, closes_at


def near(a, b):
    assert math.isclose(a, b, abs_tol=1e-6, rel_tol=1e-10), (a, b)


def audit(data, config, ledger, *, benchmark=False, memo=None):
    memo = {} if memo is None else memo
    cash, fees = config.initial_cash, 0.
    holdings, claims = {}, []
    by_date = defaultdict(list)
    for t in ledger.trades:
        by_date[t['date']].append(t)
    fills = {}
    blocked_dates = {r['date'] for r in getattr(ledger, 'blocked', [])}
    sessions = [r['date'] for r in ledger.equity]
    for signal in ledger.targets:
        future = next((d for d in sessions if d > signal['date']), None)
        if future and future not in blocked_dates and (signal['targets'] or not signal['risk_on']):
            fills[future] = signal
    max_error, max_participation = 0., 0.
    split_events = defaultdict(list)
    dividends = defaultdict(list)
    for e in data.source.splits:
        split_events[e['execution_date']].append(e)
    for e in data.source.dividends:
        dividends[e['ex_dividend_date']].append(e)
    for row in ledger.equity:
        day = row['date']
        bars = data.bars(day)
        for e in split_events[day]:
            if e['ticker'] in holdings:
                holdings[e['ticker']] *= e['split_to'] / e['split_from']
        for e in dividends[day]:
            if e['ticker'] in holdings:
                claims.append((holdings[e['ticker']] * e['cash_amount'], e['pay_date']))
        cash += sum(a for a, d in claims if d and d <= day)
        claims = [(a, d) for a, d in claims if not d or d > day]
        pre = dict(holdings)
        expected_events = []
        for t, e in data.cash_actions.items():
            if e['effective_date'] == day and t in holdings:
                q = holdings.pop(t)
                amount = q * e['cash_per_share']
                if e.get('pay_date') and e['pay_date'] <= day:
                    cash += amount
                else:
                    claims.append((amount, e.get('pay_date')))
                expected_events.append(('CASH_MERGER_CLAIM', t, q, e['cash_per_share']))
        for t, e in data.stock_actions.items():
            if e['effective_date'] == day and t in holdings:
                q = holdings.pop(t)
                if e.get('cash_per_share'):
                    amount = q * e['cash_per_share']
                    if e.get('pay_date') and e['pay_date'] <= day:
                        cash += amount
                    else:
                        claims.append((amount, e.get('pay_date')))
                    expected_events.append(('STOCK_MERGER_CASH_CLAIM', t, q, e['cash_per_share']))
                successor = e['successor_ticker']
                holdings[successor] = holdings.get(successor, 0) + q * e['shares_per_share']
        for e in data.distributions:
            q = pre.get(e['parent'], 0) * e['ratio']
            if e['ex_date'] == day and q:
                holdings[e['recipient']] = holdings.get(e['recipient'], 0) + q
                expected_events.append(('STOCK_DISTRIBUTION', e['recipient'], q, 0.))
        actual_events = []
        for t in by_date[day]:
            ticker, side, q, price = t['ticker'], t['side'], t['quantity'], t['price']
            if side not in ('BUY', 'SELL'):
                actual_events.append((side, ticker, q, price))
                continue
            assert q > 0 and float(q).is_integer()
            assert t['signal_date'] < day
            assert benchmark or ticker != 'SPY'
            near(price, bars[ticker][0])
            value = q * price
            charge = max(1., value / 400) + value * (.0025 + config.one_way_cost)
            near(t['fee'], charge)
            fees += charge
            if side == 'BUY':
                cash -= value + charge
                holdings[ticker] = holdings.get(ticker, 0) + q
            else:
                assert holdings.get(ticker, 0) + 1e-7 >= q
                cash += value - charge
                holdings[ticker] -= q
                if abs(holdings[ticker]) < 1e-9:
                    del holdings[ticker]
            assert cash >= -1e-6
            assert bars[ticker][2] > 0
            max_participation = max(max_participation, q / bars[ticker][2])
        assert sorted(expected_events) == sorted(actual_events)
        if day in fills:
            target_names = {r['ticker'] for r in fills[day]['targets']}
            assert all(holdings.get(t, 0) >= 1 for t in target_names)
            assert all(t in target_names or q < 1 for t, q in holdings.items())
        def close(t):
            mark = data.halt_marks.get(day)
            if mark and t == mark['ticker']:
                assert not bars.get(t)
                return mark['value']
            return bars[t][1]
        nav = cash + sum(q * close(t) for t, q in holdings.items()) + sum(a for a, _ in claims)
        max_error = max(max_error, abs(nav - row['nav']))
        near(nav, row['nav']); near(cash, row['cash']); near(fees, row['fees_cumulative'])
        assert len(holdings) == row['positions']
    signals = 0
    if not benchmark:
        for signal in ledger.targets:
            if not signal['risk_on']:
                assert not signal['targets']
                continue
            day = signal['date']
            if day not in memo:
                rows = population(data, day, replace(config, positions=100000), formation=True)
                for r in rows:
                    c = closes_at(data, day, r['ticker'], 64)
                    r['return_1m'] = c[0] / c[21] - 1
                    r['return_3m'] = c[0] / c[63] - 1
                memo[day] = rows
            eligible = []
            for r in memo[day]:
                price = r['raw_price']
                charge = max(1., price * .0025) + price * (.0025 + config.one_way_cost)
                if price + charge <= signal['signal_nav'] / 10 and (not signal['fresh'] or min(r['return_1m'], r['return_3m']) > 0):
                    eligible.append(r)
            wanted = eligible[:10] if len(eligible) >= 10 else []
            assert signal['eligible_count'] == len(eligible)
            assert [r['ticker'] for r in wanted] == [r['ticker'] for r in signal['targets']]
            for a, b in zip(signal['targets'], wanted):
                for key in ('risk_normalized_score', 'momentum_12_2', 'return_1m', 'return_3m'):
                    near(a[key], b[key])
                near(a['weight'], .1)
            signals += 1
    near(cash, ledger.cash)
    assert holdings.keys() == ledger.shares.keys()
    for t in holdings:
        near(holdings[t], ledger.shares[t])
    return {'status': 'PASS', 'sessions': len(ledger.equity), 'signals': signals,
            'trades': len(ledger.trades), 'max_nav_error_usd': max_error,
            'max_volume_participation': max_participation,
            'independent_vendor': False}


def financial_audit(strategy, benchmark, result):
    """Recompute financial gates without importing the shared metric functions."""
    rows = strategy.equity
    peak = rows[0]['nav']
    worst = 0.
    returns = []
    for i, row in enumerate(rows):
        peak = max(peak, row['nav'])
        worst = min(worst, (row['nav'] / peak - 1) * 100)
        if i:
            returns.append(row['nav'] / rows[i-1]['nav'] - 1)
    boundaries = [r for i, r in enumerate(rows) if (not i and strategy.first_is_month_boundary)
                  or (i and r['date'][:7] != rows[i-1]['date'][:7])]
    total = (rows[-1]['nav'] / rows[0]['nav'] - 1) * 100
    spy = (benchmark.equity[-1]['nav'] / benchmark.equity[0]['nav'] - 1) * 100
    periods = len(boundaries) - 1
    hit = 100 * sum(b['nav'] > a['nav'] for a, b in zip(boundaries, boundaries[1:])) / periods if periods else 0.
    center = sum(returns) / len(returns)
    variance = sum((r - center)**2 for r in returns) / (len(returns) - 1)
    calculated = {'Periods': periods, 'TotalReturn_pct': total, 'SPYTotalReturn_pct': spy,
                  'TotalEdgeVsSPY_pct': total - spy, 'DailyMaxDrawdown_pct': worst,
                  'PeriodHitRate_pct': hit, 'ActualFees_USD': strategy.fees,
                  'FinalNAV_USD': rows[-1]['nav'],
                  'DailySharpe_zero_rf': math.sqrt(252) * center / math.sqrt(variance) if variance else None}
    for key, value in calculated.items():
        if value is None:
            assert result[key] is None
        else:
            near(result[key], value)
    return {'status': 'PASS', 'independently_recomputed': calculated}
