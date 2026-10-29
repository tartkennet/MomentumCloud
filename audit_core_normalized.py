"""Independent signal/score/cap/timing verifier; imports no strategy module.

The data adapter supplies the frozen PIT records and verified ticker lineage.
This verifies implementation, not independent vendor provenance or alpha.
"""
import math


def positive(value, zero=False):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and (value >= 0 if zero else value > 0) else None


def closes_at(data, day, ticker, count):
    history = data.history(day, ticker, count)
    if len(history) != count or any(not bar for _, bar in history):
        return []
    events = (data.signal_splits(day, ticker) if hasattr(data, 'signal_splits')
              else [e for e in data.splits if e['ticker'] == ticker])
    closes = []
    for stamp, bar in history:
        close = positive(bar[1])
        if close is None:
            return []
        for event in events:
            if history[-1][0] < event['execution_date'] <= day and stamp < event['execution_date']:
                before, after = positive(event.get('split_from')), positive(event.get('split_to'))
                if before is None or after is None:
                    raise AssertionError('Invalid signal split')
                close *= before / after
        closes.append(close)
    return closes


def population(data, day, config, formation=False):
    """Reconstruct the entire eligible set, including excluded top raw winners."""
    records = {r.get('ticker'): r for r in data.universe(day)}
    rows = []
    for ticker, record in sorted(records.items(), key=lambda x: str(x[0])):
        name = str(record.get('name', '')).upper()
        if (record.get('active') is not True or record.get('type') != 'CS'
                or record.get('primary_exchange') not in {'XNAS', 'XNYS', 'XASE'}
                or not ticker or any(s in name for s in ('ACQUISITION', 'BLANK CHECK', ' SPAC'))):
            continue
        history = data.history(day, ticker, 253)
        if len(history) != 253 or any(not bar for _, bar in history):
            continue
        price = positive(history[0][1][1])
        if price is None or price < config.min_price:
            continue
        dollars = []
        for _, bar in history[:20]:
            close, volume = positive(bar[1]), positive(bar[2], zero=True)
            if close is not None and volume is not None:
                dollars.append(close * volume)
        if len(dollars) != 20:
            continue
        adv = math.fsum(dollars) / 20
        if adv < config.min_adv:
            continue
        closes = closes_at(data, day, ticker, 253)
        if not closes:
            continue
        momentum = closes[21] / closes[252] - 1
        returns = [closes[i] / closes[i + 1] - 1 for i in range(config.vol_returns)]
        mean = math.fsum(returns) / len(returns)
        vol = math.sqrt(math.fsum((r - mean) ** 2 for r in returns) / (len(returns) - 1))
        if momentum > 0 and math.isfinite(vol) and vol > 0:
            row = {'ticker': ticker, 'momentum_12_2': momentum, 'daily_volatility': vol,
                   'raw_price': price, 'adv20_usd': adv, 'risk_normalized_score': momentum / vol}
            if formation:
                formation_returns = [closes[i] / closes[i+1] - 1 for i in range(21,252)]
                center = math.fsum(formation_returns) / 231
                deviation = math.sqrt(math.fsum((r-center)**2 for r in formation_returns) / 230)
                if not math.isfinite(deviation) or deviation <= 0:
                    continue
                row['formation_volatility'] = deviation
                row['risk_normalized_score'] = momentum / deviation
            rows.append(row)
    return sorted(rows, key=lambda r: (-r['risk_normalized_score'], r['ticker']))


def expected_weights(rows, config):
    """Solve min(cap, lambda / vol) by bisection, independently of water filling."""
    if not rows:
        return {}
    budget = min(len(rows) / config.positions, len(rows) * config.max_weight)
    lo, hi = 0.0, max(r['daily_volatility'] for r in rows) * config.max_weight
    for _ in range(100):
        scale = (lo + hi) / 2
        total = math.fsum(min(config.max_weight, scale / r['daily_volatility']) for r in rows)
        if total < budget:
            lo = scale
        else:
            hi = scale
    return {r['ticker']: min(config.max_weight, (lo + hi) / 2 / r['daily_volatility']) for r in rows}


def near(actual, expected, label):
    if not math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-10):
        raise AssertionError(f'{label}: {actual} != {expected}')


def audit_targets(data, config, targets, trades=(), memo=None, formation=False):
    """Derive every signal date, then verify all emitted ranks and target fields."""
    previous_risk, month, expected = False, '', []
    memo = {} if memo is None else memo
    for i, day in enumerate(data.sessions):
        key = ('risk', day)
        if key not in memo:
            closes = closes_at(data, day, 'SPY', 200)
            if len(closes) != 200:
                raise AssertionError('Incomplete SPY signal history')
            memo[key] = closes[0] > math.fsum(closes) / len(closes)
        allowed = memo[key]
        if allowed and (month != day[:7] or not previous_risk):
            expected.append((day, True))
            month = day[:7]
        elif not allowed and (previous_risk or i == 0):
            expected.append((day, False))
        previous_risk = allowed
    if [(r['date'], r['risk_on']) for r in targets] != expected:
        raise AssertionError('Signal dates/regime do not match observed close rules')
    checked = 0
    for signal in targets:
        if not signal['risk_on']:
            if signal['targets'] or signal['eligible_count'] != 0:
                raise AssertionError('Risk-off target must be cash')
            continue
        key = ('population', formation, signal['date'])
        if key not in memo:
            memo[key] = population(data, signal['date'], config, formation)
        ranked = memo[key]
        chosen = ranked[:config.positions]
        if signal['eligible_count'] != len(ranked):
            raise AssertionError('Eligible population differs')
        if [r['ticker'] for r in signal['targets']] != [r['ticker'] for r in chosen]:
            raise AssertionError('Selected rank/order differs')
        weights = expected_weights(chosen, config)
        for actual, row in zip(signal['targets'], chosen):
            for name in row:
                if name != 'ticker':
                    near(actual[name], row[name], name)
            near(actual['weight'], weights[row['ticker']], 'weight')
        checked += len(ranked)
    next_day = dict(zip(data.sessions, data.sessions[1:]))
    fills = 0
    for trade in trades:
        if trade['side'] in ('BUY', 'SELL', 'BUY_CANCELLED_NO_OPEN'):
            if next_day.get(trade['signal_date']) != trade['date']:
                raise AssertionError('Trade does not execute at next observed session')
            fills += 1
    return {'status': 'PASS', 'signals_checked': len(targets), 'eligible_rows_checked': checked,
            'next_session_orders_checked': fills,
            'scope': 'Independent signal dates, eligibility, rank, weights and next-session timing; shared frozen data adapter, not independent vendor or alpha evidence.'}
