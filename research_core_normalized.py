"""One frozen Core ranking change; no production or paper identity changes."""
import math
import statistics

from momentum_core import CONFIG, adjusted_history, capped_weights, eligible, number

MODEL = 'momentum-core-risk-normalized-research-v1'


def select_targets(data, day, config=CONFIG):
    candidates = []
    records = {r.get('ticker'): r for r in data.universe(day) if eligible(r)}
    for ticker in sorted(records):
        history = data.history(day, ticker, 253)
        if len(history) != 253 or any(not row for _, row in history):
            continue
        price = number(history[0][1][1])
        liquidity = [number(bar[1]) * number(bar[2], positive=False)
                     for _, bar in history[:20]
                     if number(bar[1]) is not None and number(bar[2], positive=False) is not None]
        if price is None or price < config.min_price or len(liquidity) != 20:
            continue
        adv = statistics.fmean(liquidity)
        if adv < config.min_adv:
            continue
        closes = adjusted_history(data, day, ticker, 253)
        if not closes:
            continue
        momentum = closes[21] / closes[252] - 1
        returns = [closes[i] / closes[i + 1] - 1 for i in range(config.vol_returns)]
        volatility = statistics.stdev(returns)
        if momentum <= 0 or volatility <= 0 or not math.isfinite(volatility):
            continue
        candidates.append({'ticker': ticker, 'momentum_12_2': momentum,
                           'daily_volatility': volatility, 'raw_price': price,
                           'adv20_usd': adv, 'risk_normalized_score': momentum / volatility})
    candidates.sort(key=lambda r: (-r['risk_normalized_score'], r['ticker']))
    chosen = candidates[:config.positions]
    weights = capped_weights({r['ticker']: 1 / r['daily_volatility'] for r in chosen},
                             config.max_weight, len(chosen) / config.positions)
    for row in chosen:
        row['weight'] = weights[row['ticker']]
    return chosen, len(candidates)
