"""H1: an unlevered, benchmark-referenced aggregate stock risk budget."""
import copy
import math
import statistics

from momentum_core import CONFIG, DataBlocked, adjusted_history
from research_core_formation import select_targets as formation_targets

MODEL = 'momentum-portfolio-benchmark-risk-research-v1'


def price_returns(data, day, ticker, count):
    closes = adjusted_history(data, day, ticker, count+1)
    if len(closes) != count+1:
        raise DataBlocked(f'Missing past portfolio-risk history {ticker} {day}')
    return [closes[i]/closes[i+1]-1 for i in range(count)]


def risk_budget(data, day, targets, config=CONFIG):
    if not targets:
        return []
    rows = copy.deepcopy(targets)
    basket = [0.] * config.vol_returns
    for row in rows:
        if not math.isfinite(row['weight']) or row['weight'] <= 0:
            raise DataBlocked('Invalid original risk weight')
        returns = price_returns(data, day, row['ticker'], config.vol_returns)
        for i, r in enumerate(returns):
            basket[i] += row['weight'] * r
    portfolio_vol = statistics.stdev(basket)
    spy_vol = statistics.stdev(price_returns(data, day, 'SPY', config.vol_returns))
    if min(portfolio_vol, spy_vol) <= 0 or not all(math.isfinite(v) for v in (portfolio_vol, spy_vol)):
        raise DataBlocked('Invalid portfolio/benchmark variance')
    scale = min(1., spy_vol / portfolio_vol)
    for row in rows:
        row.update(weight=row['weight']*scale, portfolio_risk_scale=scale,
                   portfolio_vol63=portfolio_vol, benchmark_vol63=spy_vol)
    return rows


def select_targets(data, day, config=CONFIG, *, saved_signal=None):
    if saved_signal is None:
        targets, count = formation_targets(data, day, config)
    else:
        assert saved_signal['date'] == day and saved_signal['risk_on']
        targets, count = saved_signal['targets'], saved_signal['eligible_count']
    return risk_budget(data, day, targets, config), count
