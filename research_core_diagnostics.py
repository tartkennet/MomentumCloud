"""Fixed descriptive reporting. No selection, parameters or approval changes."""
import math
import statistics


def performance(rows, field='nav'):
    returns = [float(b[field]) / float(a[field]) - 1 for a, b in zip(rows, rows[1:])]
    deviation = statistics.stdev(returns) if len(returns) > 1 else 0
    sharpe = math.sqrt(252) * statistics.fmean(returns) / deviation if deviation else None
    start = float(rows[0][field])
    peak, dd = start, 0.
    for r in rows:
        value = float(r[field])
        peak = max(peak, value)
        dd = min(dd, 100 * (value / peak - 1))
    return {'return_pct': 100 * (float(rows[-1][field]) / start - 1),
            'max_drawdown_pct': dd, 'daily_sharpe_zero_rf': sharpe,
            'sessions': len(returns)}


def describe(rows):
    result = {'full': {'strategy': performance(rows), 'SPY': performance(rows, 'spy_nav')},
              'calendar_years': {}, 'sharpe_convention': 'Daily simple USD returns, sample stdev, sqrt(252), zero risk-free rate; cash interest also zero.'}
    for year in sorted({r['date'][:4] for r in rows}):
        indices = [i for i, r in enumerate(rows) if r['date'].startswith(year)]
        sample = rows[max(0, indices[0] - 1):indices[-1] + 1]
        result['calendar_years'][year] = {'strategy': performance(sample), 'SPY': performance(sample, 'spy_nav'),
                                        'fees_usd': float(sample[-1]['fees_cumulative']) - float(sample[0]['fees_cumulative'])}
    result['later_segment'] = None
    later = [r for r in rows if r['date'] >= '2026-09-01']
    if len(later) > 1:
        result['later_segment'] = {'strategy': performance(later), 'SPY': performance(later, 'spy_nav'),
                                   'certified_untouched_out_of_sample': False}
    return result
