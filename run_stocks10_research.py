"""Run only the preregistered Stocks10 hypotheses; saved inputs, no orders."""
import argparse
import copy
import hashlib
import json
import socket
from dataclasses import replace
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import momentum_core as core
from momentum_core_data import atomic_json
from research_core_actions import supplement
from research_core_ledger import complete_data
from research_core_diagnostics import performance, describe
from run_core_normalized_research import verify_inputs, payment_policy
from run_core_risk_research import make_data, EXTENSION_END, DELAYS
from research_stocks10 import Stocks10Ledger, MODEL, APGE_COMPLETION
from audit_stocks10 import audit, financial_audit


def fx_rows(path):
    rows = {}
    for node in ElementTree.parse(path).iter():
        if 'time' not in node.attrib:
            continue
        rates = {c.attrib.get('currency'): float(c.attrib['rate']) for c in node if 'rate' in c.attrib}
        if 'USD' in rates and 'SEK' in rates:
            value = rates['SEK'] / rates['USD']
            if value <= 0:
                raise core.DataBlocked('Nonpositive ECB cross')
            rows[node.attrib['time']] = value
    if not rows:
        raise core.DataBlocked('No ECB USD/SEK cross history')
    return rows


def prior_fx(rows, day):
    prior = max((d for d in rows if d < day), default=None)
    if not prior or (date.fromisoformat(day) - date.fromisoformat(prior)).days > 7:
        raise core.DataBlocked('Missing/stale previously published FX: ' + day)
    return {'date': prior, 'usdsek': rows[prior]}


def converted(ledger, rates):
    return [dict(r, nav=r['nav'] * prior_fx(rates, r['date'])['usdsek']) for r in ledger.equity]


def run(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'results.json').exists():
        raise ValueError('Never overwrite a previous study')
    input_hash = verify_inputs(args.cache, args.manifest)
    rates = fx_rows(args.fx)
    data = complete_data(supplement(make_data(args.cache, EXTENSION_END, True)))
    data.source.cash_actions = dict(data.source.cash_actions, APGE=copy.deepcopy(APGE_COMPLETION))
    initial_fx = prior_fx(rates, data.sessions[0])
    initial_usd = 20000 / initial_fx['usdsek']
    source_files = ['research_stocks10.py', 'audit_stocks10.py', 'run_stocks10_research.py', 'docs/STOCKS10_PROTOCOL_20261031.md']
    report = {'model': MODEL, 'status': 'RUNNING', 'evidence_class': 'DEVELOPMENT_RESEARCH',
              'certified_untouched_out_of_sample': False, 'live_approved': False,
              'broker_orders_enabled': False, 'initial_sek': 20000, 'initial_fx': initial_fx,
              'start': data.sessions[0], 'end': data.sessions[-1], 'sessions': len(data.sessions),
              'input_manifest_sha256': input_hash,
              'fx_sha256': hashlib.sha256(Path(args.fx).read_bytes()).hexdigest(),
              'source_files': {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in source_files},
              'supplemental_cash_actions': {'APGE': APGE_COMPLETION},
              'attempts': [], 'comparators': {}}
    for name, path in [('H3', 'docs/CORE_PORTFOLIO_H3_RESULTS_20261029.json'), ('Core', 'docs/CORE_RISK_RESULTS_20261029.json')]:
        saved = json.loads(Path(path).read_text())
        key = 'attempts' if 'attempts' in saved else 'cases'
        matches = [a for a in saved[key] if a.get('phase') == 'extension' and a.get('policy') == 'assumed_5' and a.get('cost') == .0015 and a.get('halt_mark_policy', 'last_quote') == 'last_quote']
        if name == 'Core':
            matches = [a for a in saved[key] if a.get('phase') == 'extension' and a['name'] == 'baseline_assumed_5_15bps']
        if matches:
            report['comparators'][name] = {'metrics': matches[0]['metrics'], 'currency': 'USD',
                'start_capital_usd': 100000, 'cost_basis': 'saved 15bp all-in; not Stocks10 retail costs',
                'source': path, 'replayed': False}
    populations, independent = {}, {}
    for fresh in (False, True):
        if fresh and report.get('A_status') == 'PAPER_ONLY':
            break
        variant = 'B' if fresh else 'A'
        for mark in ('last_quote', 'offer_value'):
            complete_data(data, mark)
            for delay in DELAYS:
                assumptions = payment_policy(data, delay)
                for spread in (.0015, .003):
                    name = f'{variant}_{delay}_{mark}_{spread}'
                    attempt = {'name': name, 'variant': variant, 'delay': delay, 'mark': mark,
                               'execution_cost': spread, 'payment_assumptions': assumptions, 'status': 'RUNNING'}
                    report['attempts'].append(attempt)
                    atomic_json(output / 'results.json', report)
                    print('START ' + name, flush=True)
                    try:
                        config = replace(core.CONFIG, model=MODEL, positions=10, initial_cash=initial_usd, one_way_cost=spread)
                        s = Stocks10Ledger(cash=initial_usd, fresh=fresh)
                        b = Stocks10Ledger(cash=initial_usd, benchmark_account=True)
                        s.first_is_month_boundary = data.first_is_month_boundary()
                        for day in data.sessions:
                            data.set_day(day)
                            b.step(data, day, config, benchmark=True)
                            s.step_stocks(data, day, config, populations)
                        metrics, periods = core.metrics(s, b)
                        metrics['DailySharpe_zero_rf'] = performance(s.equity)['daily_sharpe_zero_rf']
                        # Independent transaction/claims/cash arithmetic and independent eligible-universe ranking.
                        audit_s = audit(data, config, s, memo=independent)
                        audit_b = audit(data, config, b, benchmark=True)
                        financial = financial_audit(s, b, metrics)
                        gates = core.gates(metrics)
                        passed = all(g['pass'] for g in gates) and not s.blocked
                        folder = output / name
                        folder.mkdir()
                        atomic_json(folder / 'strategy.json', s.to_dict())
                        atomic_json(folder / 'benchmark.json', b.to_dict())
                        daily = [dict(r, spy_nav=q['nav']) for r, q in zip(s.equity, b.equity)]
                        attempt.update(status='COMPLETE', decision='PAPER_ONLY' if passed else 'NO_GO',
                            metrics=metrics, gates=gates, audit=audit_s, benchmark_audit=audit_b, financial_audit=financial,
                            sek=performance(converted(s, rates)), spy_sek=performance(converted(b, rates)),
                            diagnostics=describe(daily), blocked=s.blocked,
                            benchmark_fees_usd=b.fees,
                            rounding_cash_average_pct=sum(r['cash']/r['nav']*100 for r in s.equity)/len(s.equity),
                            maximum_positions=max(r['positions'] for r in s.equity))
                        atomic_json(folder / 'result.json', attempt)
                        print('DONE ' + name + ' ' + json.dumps(metrics), flush=True)
                    except Exception as exc:
                        attempt.update(status='BLOCKED', decision='NO_GO', error=f'{type(exc).__name__}: {exc}')
                        print('BLOCKED ' + name + ' ' + attempt['error'], flush=True)
                        # A deterministic technical block is not 20 experiments.
                        # Preserve the failed attempt and fix it before continuing.
                        report['status'] = 'TECHNICAL_BLOCK'
                        atomic_json(output / 'results.json', report)
                        raise
                    atomic_json(output / 'results.json', report)
        report[variant + '_status'] = 'PAPER_ONLY' if all(a['decision'] == 'PAPER_ONLY' for a in report['attempts'] if a['variant'] == variant) else 'NO_GO'
        atomic_json(output / 'results.json', report)
    report['status'] = report.get('B_status', report['A_status'])
    report['completed'] = True
    atomic_json(output / 'results.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cache', 'manifest', 'fx', 'output'):
        p.add_argument('--' + name, required=True)
    args = p.parse_args()
    def blocked(*a, **kw):
        raise RuntimeError('Network forbidden during offline Stocks10 replay')
    socket.socket.connect = blocked
    socket.create_connection = blocked
    run(args)
