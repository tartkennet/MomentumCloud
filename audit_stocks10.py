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
    assert holdings == ledger.shares
    return {'status': 'PASS', 'sessions': len(ledger.equity), 'signals': signals,
            'trades': len(ledger.trades), 'max_nav_error_usd': max_error,
            'max_volume_participation': max_participation,
            'independent_vendor': False}
