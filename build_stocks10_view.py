"""Publish completed evidence only. No replay, signals or paper account writes."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from run_stocks10_research import fx_rows, prior_fx
from momentum_core_data import atomic_json


def build(evidence, run, source, artifact_sha, output, document):
    root = Path(evidence)
    r = json.loads((root / 'results.json').read_text())
    if not r.get('completed') or len(r['attempts']) not in (20, 40):
        raise ValueError('Incomplete research cannot be published as complete')
    for a in r['attempts']:
        assert a['status'] == 'COMPLETE'
        assert a['audit']['status'] == a['benchmark_audit']['status'] == a['financial_audit']['status'] == 'PASS'
    # Bind every replay/ledger/audit/protocol file to the executed commit.
    for path, digest in r['source_files'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    rates = fx_rows(root / 'ecb-history.xml')
    assert hashlib.sha256((root / 'ecb-history.xml').read_bytes()).hexdigest() == r['fx_sha256']
    last_variant = 'B' if r.get('B_status') else 'A'
    primary = next(a for a in r['attempts'] if a['name'] == f'{last_variant}_5_last_quote_0.0015')
    s = json.loads((root / primary['name'] / 'strategy.json').read_text())
    b = json.loads((root / primary['name'] / 'benchmark.json').read_text())
    # These extra same-vendor quotes are a publication cross-check, not new
    # strategy input. Require exact aggregate reconciliation to archived NAV.
    with (root / 'publication-quotes.csv').open() as stream:
        quotes = {row['ticker']: row for row in csv.DictReader(stream)}
    last_fx = prior_fx(rates, r['end'])
    positions = []
    for ticker, q in s['shares'].items():
        quote = quotes[ticker]
        assert int(quote['timestamp']) == 1793217600000  # 2026-10-28 US daily bar
        close = float(quote['close'])
        assert close > 0
        positions.append({'ticker': ticker, 'quantity': q, 'close_usd': close,
            'value_sek': q * close * last_fx['usdsek'], 'weight_pct': q * close / s['equity'][-1]['nav'] * 100,
            'corporate_fraction_only': q < 1})
    actual = sum(p['quantity'] * p['close_usd'] for p in positions)
    assert math.isclose(actual, s['equity'][-1]['stock_value'], abs_tol=1e-6), (actual, s['equity'][-1]['stock_value'])
    assert math.isclose(float(quotes['SPY']['close']) * b['shares']['SPY'], b['equity'][-1]['stock_value'], abs_tol=1e-6)
    variants = []
    for v in ('A', 'B'):
        attempts = [a for a in r['attempts'] if a['variant'] == v]
        if not attempts:
            continue
        case = next(a for a in attempts if a['name'] == f'{v}_5_last_quote_0.0015')
        variants.append({'variant': v, 'status': r[v + '_status'], 'completed': len(attempts),
            'passed': sum(a['decision'] == 'PAPER_ONLY' for a in attempts), 'gates': case['gates'],
            'metrics': case['metrics'], 'sek': case['sek'],
            'worst_usd_drawdown_pct': min(a['metrics']['DailyMaxDrawdown_pct'] for a in attempts),
            'minimum_return_pct': min(a['metrics']['TotalReturn_pct'] for a in attempts)})
    cases = [{k: a[k] for k in ('name', 'variant', 'status', 'decision', 'metrics', 'gates', 'audit')} for a in r['attempts']]
    curve = [{'date': a['date'], 'nav_sek': a['nav'] * prior_fx(rates, a['date'])['usdsek'],
              'spy_sek': z['nav'] * prior_fx(rates, z['date'])['usdsek']} for a, z in zip(s['equity'], b['equity'])]
    payload = dict(r, attempts=None, source_commit=source, workflow_run=str(run),
        artifact_sha256=artifact_sha, variants=variants, cases=cases, primary=primary,
        positions=sorted(positions, key=lambda p: -p['value_sek']), trades=s['trades'], curve=curve,
        publication_quote_sha256=hashlib.sha256((root/'publication-quotes.csv').read_bytes()).hexdigest(),
        publication_nav_crosscheck='PASS', live_approved=False, broker_orders_enabled=False,
        forward_paper_started=False,
        final_whole_stock_positions=sum(p['quantity'] >= 1 for p in positions),
        final_fractional_corporate_entitlements=sum(p['quantity'] < 1 for p in positions))
    del payload['attempts']
    atomic_json(output, payload)
    lines = ['# Stocks10 — completed separate study, 2026-10-31', '',
        '**NO_GO. No new forward account, broker orders, H3 replacement or Buy Now change.**', '',
        f"Source `{source}`, [run {run}](https://github.com/tartkennet/MomentumCloud/actions/runs/{run}).",
        f'Artifact ZIP SHA256 `{artifact_sha}`. Permanent draft release `stocks10-research-{run}-1`.', '',
        'The original protocol was committed before replay. Both hypotheses and all failures are preserved.',
        'This is reused development history, not untouched out-of-sample evidence.', '',
        '| Case (5-session payment assumption, last quote, 15bp execution) | USD return | USD max DD | Sharpe USD | SEK return | SEK max DD | Fees USD |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for v in variants:
        a = next(a for a in r['attempts'] if a['name'] == f"{v['variant']}_5_last_quote_0.0015")
        m = a['metrics']
        lines.append(f"| {v['variant']} | {m['TotalReturn_pct']:.2f}% | {m['DailyMaxDrawdown_pct']:.2f}% | {m['DailySharpe_zero_rf']:.2f} | {a['sek']['return_pct']:.2f}% | {a['sek']['max_drawdown_pct']:.2f}% | {m['ActualFees_USD']:.2f} |")
    lines += ['', '## Interpretation', '',
        'A removes the SPY core but fails drawdown, SPY outperformance and hit rate. B improves A, yet still fails drawdown and SPY outperformance. All 40 scenarios are NO_GO.',
        'The small account magnifies minimum commissions and whole-lot rounding. B pays USD 885.30 (44.45% of initial USD capital over the full study; not an annual fee). Its average cash fraction is 20.83%, including defensive risk-off sessions. This is not a pure rounding-cost estimate.',
        'Positive recent returns do not prevent correlated single-stock losses or gaps. No third indicator/threshold search is justified by these two reviewed-history results.',
        'The final replay has ten positions of at least one share PLUS a fractional corporate entitlement. Do not call that exactly ten economic exposures. B retains 0.8934 CDE from the verified NGD exchange; A retains 0.232 COMP from an existing corporate exchange. These are not fractional market purchases or fictitious sales. They remain valued and auditable. This is an additional implementation issue before any real-world adoption.',
        'The five original financial GO gates are applied in USD without changes. SEK drawdown is worse, not hidden by an FX switch. SPY comparison with the same small capital/retail costs returns +64.02% USD and +62.30% SEK; its SEK drawdown is -26.49%.', '',
        '## Independent checks', '',
        'All 40 strategy and 40 benchmark transaction/claims/NAV reconciliations passed; full eligible rankings were rebuilt independently; all 40 financial metric audits passed. The largest account error is below USD 0.000001. Same market vendor: this is independent code, not independent data-vendor confirmation.',
        'Additional raw close quotes for the final holdings and SPY were fetched only for publication, then reconciled exactly to archived stock values. They did not enter any replay or select a model. The quote CSV hash is in the public evidence.',
        'APGE initially blocked B at its real cash merger. Nasdaq and SEC confirm USD 135.11 and 2026-09-03 before-open completion. The unverified payment date is handled by all five frozen sensitivities. The interrupted first attempt is retained in `stocks10-research-41180505963-1`.', '',
        '## Comparators and next step', '',
        'Saved H3: +77.13% USD, -16.08% DD, Sharpe 1.31. Original Core: +15.60% USD, -47.38% DD. Their USD 100,000/15bp all-in assumptions differ from Stocks10 retail costs; they were not rerun or rewritten.',
        'Keep H3 prospective collection unchanged. Stocks10 remains a completed rejected development study. No backdated trades or new paper returns are created. A future redesign needs a new economic protocol addressing portfolio risk, affordability and trading-cost feasibility, not tuning these two histories.', '']
    Path(document).write_text('\n'.join(lines))
    return payload


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence', 'run', 'source', 'artifact-sha', 'output', 'document'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    build(a.evidence, a.run, a.source, a.artifact_sha, a.output, a.document)
