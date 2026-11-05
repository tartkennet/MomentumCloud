"""Capital-independent Quality ranking for the Avanza paper decision aid."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import math
from pathlib import Path

import momentum_core as core
from audit_core_normalized import closes_at
from collect_quality import fundamentals, market_universe, math_close
from momentum_core_data import atomic_json, read_json
from quality_audit import audit_selection
from quality_forward import NY
from quality_strategy import choose, rank
from research_core_actions import supplement
from run_core_risk_research import make_data

VERSION = 'avanza10-paper-v2'
MIN_COVERAGE = .90


def build_snapshot(report, previous, data, originals):
    """Reuse same-session observations and collect only newly included names."""
    now = datetime.fromisoformat(report['generated_at'])
    month = now.astimezone(NY).strftime('%Y-%m')
    selection = previous.get('selection') if previous.get('version') == VERSION else None
    day = report['price_as_of']
    universe, _, risk_on = market_universe(data, day, math.inf)
    if risk_on is not report.get('risk_on') or day != data.sessions[-1]:
        raise ValueError('MARKET_OBSERVATION_MISMATCH')
    prior = {(r['ticker'], r['cik']): r for r in report['candidates'] if r.get('price_as_of') == day}
    missing = [r for r in universe if (r['ticker'], r['cik']) not in prior]
    with ThreadPoolExecutor(max_workers=4) as pool:
        added = list(pool.map(lambda row: fundamentals(row, originals), missing))
    resolved = [prior[(r['ticker'], r['cik'])] for r in universe if (r['ticker'], r['cik']) in prior] + added
    coverage = sum(r['resolved'] is True for r in resolved) / len(universe) if universe else 0.
    valid = [r for r in resolved if r.get('data_status') == 'VERIFIED' and r['fundamental_audit']['status'] == 'PASS']
    ranked = rank(valid)
    audit = audit_selection(valid, choose(valid, math.inf), math.inf)
    spy = closes_at(data, day, 'SPY', 253)
    if len(spy) != 253:
        raise ValueError('AVANZA_BENCHMARK_CHECK_FAILED')
    for row in ranked:
        prices = closes_at(data, day, row['ticker'], 253)
        if len(prices) != 253 or not (math_close(row['relative_strength'], (prices[0]/prices[126])/(spy[0]/spy[126])-1)
                and prices[0] > sum(prices[:200])/200):
            raise ValueError('AVANZA_MOMENTUM_CHECK_FAILED')
    new_month = not selection or selection['month'] < month
    newly_complete = selection and selection.get('target_count', 0) < 10 and audit['targets'] == 10
    if risk_on and coverage >= MIN_COVERAGE and ranked and (new_month or newly_complete):
        selection = dict(month=month, as_of=day, usdsek=report['fx']['usdsek'], observed_at=report['generated_at'],
                         target_count=audit['targets'],
                         rows=[{k: r[k] for k in ('ticker', 'name', 'sic', 'division', 'cik', 'price_usd', 'quality_score')}
                               for r in ranked])
    current_ids = {r['ticker']: str(r['cik']).zfill(10) for r in data.universe(day)
                   if core.eligible(r) and r.get('cik')}
    prices = data.bars(day)
    quotes = {r['ticker']: r['price_usd'] for r in universe}
    if selection:
        for r in selection['rows']:
            t = r['ticker']
            mark = prices.get(t, [None, None])[1]
            changed = any(selection['as_of'] < s['execution_date'] <= day
                          for s in data.splits_by_ticker.get(t, ()))
            if current_ids.get(t) != r['cik'] or changed or not isinstance(mark, (int, float)) or not math.isfinite(mark) or mark <= 0:
                quotes.pop(t, None)
            else:
                quotes[t] = mark
    return dict(version=VERSION, mode='PAPER_ONLY', selection=selection, quotes=quotes, quotes_as_of=day,
                market_verified=True, selection_verified=coverage >= MIN_COVERAGE, coverage=coverage,
                universe_count=len(universe), qualified_count=len(ranked), independent_selection=audit,
                reused_fundamentals=len(resolved)-len(added), errors=[],
                gaps=[dict(ticker=r['ticker'], reason=r.get('reason', 'SOURCE_GAP')) for r in resolved if not r['resolved']])


def main():
    p = argparse.ArgumentParser()
    for name in ('report', 'previous', 'cache', 'originals', 'output'):
        p.add_argument('--'+name, required=True, type=Path)
    args = p.parse_args()
    report = read_json(args.report)
    previous = read_json(args.previous) if args.previous.is_file() else {}
    try:
        if (report.get('status') == 'COLLECTION_FAILED' or not report.get('price_as_of') or
                not isinstance(report.get('risk_on'), bool) or not (report.get('fx') or {}).get('usdsek') or
                not (report.get('audits') or {}).get('selection')):
            raise ValueError('NO_VERIFIED_CURRENT_MARKET_INPUT')
        end = (datetime.fromisoformat(report['generated_at']).date() - timedelta(days=1)).isoformat()
        data = supplement(make_data(args.cache, end, True))
        snapshot = build_snapshot(report, previous, data, args.originals)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, AssertionError) as exc:
        error = str(exc) if isinstance(exc, ValueError) and str(exc).isupper() else type(exc).__name__
        snapshot = dict(version=VERSION, mode='PAPER_ONLY', quotes={}, quotes_as_of=report.get('price_as_of'),
                        selection=previous.get('selection') if previous.get('version') == VERSION else None,
                        market_verified=False, selection_verified=False, errors=[error])
    atomic_json(args.output, snapshot)
    print('AVANZA10', {k: snapshot.get(k) for k in (
        'version', 'quotes_as_of', 'market_verified', 'selection_verified', 'coverage',
        'universe_count', 'qualified_count', 'reused_fundamentals', 'errors'
    )}, flush=True)


if __name__ == '__main__':
    main()
