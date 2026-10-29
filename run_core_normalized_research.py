"""Offline fixed ranking test. Reuse saved controls; never search parameters."""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import json
import socket
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path

import momentum_core as core
from audit_core_normalized import audit_targets
from momentum_core_data import atomic_json
from research_core_normalized import MODEL, select_targets
from run_core_risk_research import (CUTOFF, DELAYS, EXTENSION_END, START,
                                    audit, extension_metrics, make_data, policy_actions, replay)
from run_momentum_core import source_fingerprint, write_csv

ROOT = Path(__file__).resolve().parent
FILES = ('research_core_normalized.py', 'audit_core_normalized.py',
         'run_core_normalized_research.py', 'run_core_risk_research.py',
         'audit_core_risk_research.py', 'tests/test_core_normalized.py',
         'docs/CORE_RISK_NORMALIZED_PROTOCOL_20261029.md')


def fingerprint():
    hashes = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in FILES}
    return hashlib.sha256(json.dumps({'core': source_fingerprint(), 'files': hashes},
                                    sort_keys=True).encode()).hexdigest()


def verify_inputs(cache, manifest):
    manifest = json.loads(Path(manifest).read_text())
    files = manifest['input_files']
    if len(files) != 1001:
        raise core.DataBlocked('Unexpected frozen input manifest')
    for name, expected in files.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise core.DataBlocked('Unsafe input manifest path')
        path = Path(cache) / relative
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise core.DataBlocked(f'Immutable input mismatch: {name}')
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


@contextmanager
def candidate_selection():
    original = core.select_targets
    cached = functools.lru_cache(maxsize=None)(select_targets)
    def independent_copy(data, day, config):
        return copy.deepcopy(cached(data, day, config))
    core.select_targets = independent_copy
    try:
        yield
    finally:
        core.select_targets = original


def save_case(folder, data, config, strategy, benchmark, result, periods, attempt, study):
    folder.mkdir(parents=True, exist_ok=True)
    checks = core.gates(result)
    decision = dict(attempt, model=MODEL, start=START, end=strategy.last_date,
                    status='PAPER_ONLY' if all(g['pass'] for g in checks) else 'NO_GO',
                    metrics=result, gates=checks, config=asdict(config),
                    source_fingerprint=source_fingerprint(), study_fingerprint=study,
                    input_fingerprint=data.input_fingerprint(),
                    evidence_class='DEVELOPMENT_RESEARCH', certified_untouched_holdout=False,
                    forward_paper=False, live_approved=False, broker_orders_enabled=False,
                    event_cache_files={'splits': f'splits-2022-06-30-{strategy.last_date}-v1.json.gz',
                                       'dividends': f'dividends-{START}-{strategy.last_date}-v1.json.gz'})
    write_csv(folder / 'Momentum_core_daily.csv', [dict(s, spy_nav=b['nav'])
              for s, b in zip(strategy.equity, benchmark.equity)])
    write_csv(folder / 'Momentum_core_trades.csv', strategy.trades)
    write_csv(folder / 'Momentum_core_periods.csv', periods)
    atomic_json(folder / 'Momentum_core_targets.json', strategy.targets)
    atomic_json(folder / 'Momentum_core_state.json', strategy.to_dict())
    atomic_json(folder / 'Momentum_core_decision.json', decision)
    atomic_json(folder / 'experiment_facts.json', {'cash_actions': data.cash_actions, 'stock_actions': data.stock_actions})
    atomic_json(folder / 'checkpoint.json', {'strategy': strategy.to_dict(), 'benchmark': benchmark.to_dict()})
    return decision


def render_report(register, path):
    rows = ['# Core risk-normalized ranking — 29 October 2026', '',
            'All observations are previously inspected development history. No live approval.', '',
            f"Study fingerprint: `{register['study_fingerprint']}`.", '',
            '| Phase | Payment policy | Cost/side | Candidate net % | Baseline net % | Candidate drawdown % | Failed gates |',
            '|---|---|---:|---:|---:|---:|---|']
    for a in register['attempts']:
        if a['status'] != 'COMPLETE':
            rows.append(f"| {a['phase']} | {a['policy']} | {a['cost']*10000:.0f} bp | {a['status']} | — | — | {a.get('error_type', '')} |")
            continue
        m = a['metrics']
        failed = ', '.join(g['gate'] for g in a['gates'] if not g['pass']) or 'none (PAPER_ONLY)'
        rows.append(f"| {a['phase']} | {a['policy']} | {a['cost']*10000:.0f} bp | {m['TotalReturn_pct']:.4f} | {a['control_metrics']['TotalReturn_pct']:.4f} | {m['DailyMaxDrawdown_pct']:.4f} | {failed} |")
    rows += ['', 'The historical boundary is 2026-09-01; extended rows retain the same account through 2026-10-28.',
             'Later-segment metrics are preserved separately in the JSON; neither segment is an untouched holdout.',
             'All five payment policies and both costs are retained. Assumed merger payment dates are unverified.',
             'Independent ranking/timing and accounting checks validate implementation, not independent market evidence.',
             'Vendor backfill, unverified payment dates, opening liquidity and actual execution costs remain limitations.',
             'The five existing gates and original Core paper identity are unchanged. No parameter is selected after results.', '']
    Path(path).write_text('\n'.join(rows))


def run(args):
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    register_path = output / 'attempts.json'
    if register_path.exists():
        raise ValueError('Use a fresh output directory; preserve previous attempts')
    expected = json.loads((ROOT / 'docs/CORE_RISK_RESULTS_20261029.json').read_text())
    if source_fingerprint() != expected['verification']['source_fingerprint']:
        raise core.DataBlocked('Original Core source changed')
    manifest_hash = verify_inputs(args.cache_dir, args.manifest)
    study = fingerprint()
    control_register = json.loads((Path(args.controls_dir) / 'attempts.json').read_text())
    if not control_register['all_attempts_completed'] or len(control_register['attempts']) != 60:
        raise core.DataBlocked('Incomplete saved controls')
    controls = {(a['phase'], a['name']): a for a in control_register['attempts']}
    for a in expected['cases']:
        if a['name'].startswith('baseline_'):
            saved = controls[(a['phase'], a['name'])]
            if saved['metrics'] != a['metrics'] or saved['gates'] != a['gates'] or saved['accounting_audit'] != 'PASS':
                raise core.DataBlocked('Saved control differs from verified main evidence')
    register = {'model': MODEL, 'study_fingerprint': study, 'core_fingerprint': source_fingerprint(),
                'frozen_input_manifest_fingerprint': manifest_hash,
                'input_files_verified': 1001, 'expected_attempts': 20,
                'evidence_class': 'DEVELOPMENT_RESEARCH', 'certified_untouched_holdout': False,
                'live_approved': False, 'broker_orders_enabled': False, 'attempts': [],
                'all_attempts_completed': False, 'controls_reused_without_rerun': 20}
    atomic_json(register_path, register)
    checkpoints = {}
    audit_memo = {}
    with candidate_selection():
        for phase, end in (('historical', CUTOFF), ('extension', EXTENSION_END)):
            data = make_data(args.cache_dir, end, True)
            for delay in DELAYS:
                data.cash_actions, assumptions = policy_actions(data, delay)
                policy = 'locked' if delay is None else f'assumed_{delay}'
                for cost in (.0015, .003):
                    name = f'normalized_{policy}_{round(cost * 10000)}bps'
                    control = controls[(phase, f'baseline_{policy}_{round(cost * 10000)}bps')]
                    attempt = dict(phase=phase, name=name, policy=policy, delay=delay, cost=cost,
                                   payment_assumptions=assumptions, status='RUNNING',
                                   control_metrics=control['metrics'], control_gates=control['gates'])
                    register['attempts'].append(attempt)
                    atomic_json(register_path, register)
                    print(f'START {phase} {name}', flush=True)
                    try:
                        config = replace(core.CONFIG, model=MODEL, one_way_cost=cost)
                        checkpoint = None
                        sessions = None
                        if phase == 'extension':
                            if name not in checkpoints:
                                raise core.DataBlocked('Historical checkpoint unavailable')
                            checkpoint = checkpoints[name]
                            sessions = [d for d in data.sessions if d > CUTOFF]
                        s, b, result, periods = replay(data, config, checkpoint=checkpoint, sessions=sessions)
                        if checkpoint:
                            for field in ('equity', 'trades', 'targets'):
                                assert getattr(s, field)[:len(checkpoint[0][field])] == checkpoint[0][field]
                            assert b.equity[:len(checkpoint[1]['equity'])] == checkpoint[1]['equity']
                        folder = output / phase / name
                        decision = save_case(folder, data, config, s, b, result, periods, attempt, study)
                        accounting = audit(args.cache_dir, folder)
                        selection = audit_targets(data, config, s.targets, s.trades, audit_memo)
                        atomic_json(folder / 'Momentum_core_selection_audit.json', selection)
                        attempt.update(status='COMPLETE', decision_status=decision['status'], metrics=result,
                                       gates=decision['gates'], accounting_audit=accounting['status'],
                                       max_nav_error_usd=accounting['max_nav_error_usd'], selection_audit=selection,
                                       input_fingerprint=data.input_fingerprint())
                        if phase == 'historical':
                            # Reload the actual saved checkpoint rather than retaining an in-memory shortcut.
                            saved = json.loads((folder / 'checkpoint.json').read_text())
                            checkpoints[name] = saved['strategy'], saved['benchmark']
                        else:
                            attempt['extension_metrics'] = extension_metrics(s, b)
                            attempt['extension_metrics']['evidence_class'] = 'DEVELOPMENT_RESEARCH'
                            attempt['control_extension_metrics'] = control['extension_metrics']
                        print('DONE ' + phase + ' ' + name + ' ' + json.dumps(result), flush=True)
                    except core.DataBlocked as exc:
                        attempt.update(status='DATA_BLOCKED', error_type=type(exc).__name__, error=str(exc))
                    except Exception as exc:
                        attempt.update(status='VALIDATION_ERROR', error_type=type(exc).__name__, error=str(exc))
                        raise
                    finally:
                        atomic_json(register_path, register)
                        render_report(register, output / 'report.md')
    assert fingerprint() == study
    verify_inputs(args.cache_dir, args.manifest)
    register['all_attempts_completed'] = (len(register['attempts']) == 20
                and all(a['status'] == 'COMPLETE' for a in register['attempts']))
    register['historical_all_gate_passes'] = sum(a.get('decision_status') == 'PAPER_ONLY' for a in register['attempts'])
    atomic_json(register_path, register)
    render_report(register, output / 'report.md')
    return register


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cache-dir', 'manifest', 'controls-dir', 'output-dir'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    def blocked(*args, **kwargs):
        raise RuntimeError('Network forbidden in frozen offline experiment')
    socket.socket.connect = blocked
    socket.create_connection = blocked
    try:
        result = run(args)
    except Exception as exc:
        folder = Path(args.output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        atomic_json(folder / 'study_error.json', {'status': 'STUDY_BLOCKED',
                    'error_type': type(exc).__name__, 'error': str(exc),
                    'live_approved': False, 'broker_orders_enabled': False})
        raise
    raise SystemExit(0 if result['all_attempts_completed'] else 1)
