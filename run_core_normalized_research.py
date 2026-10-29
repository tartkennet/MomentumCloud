"""Offline fixed ranking test. Reuse saved controls; never search parameters."""
from __future__ import annotations

import argparse
import copy
import csv
import functools
import hashlib
import bisect
import io
import json
import runpy
import socket
import sys
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict, replace
from pathlib import Path

import momentum_core as core
from audit_core_normalized import audit_targets
from momentum_core_data import atomic_json
from research_core_normalized import MODEL, select_targets
from research_core_actions import EXTRA_CASH_ACTIONS, supplement
from research_core_ledger import (ResearchLedger, complete_data, STOCK_COMPLETIONS,
                                  CASH_COMPLETIONS, DISTRIBUTIONS)
from research_core_diagnostics import describe, performance
from run_core_risk_research import (CUTOFF, DELAYS, EXTENSION_END, START,
                                    audit, extension_metrics, make_data, policy_actions, replay)
from run_momentum_core import source_fingerprint, write_csv

ROOT = Path(__file__).resolve().parent
FILES = ('research_core_normalized.py', 'audit_core_normalized.py',
         'research_core_ledger.py', 'audit_core_research_account.py',
         'tests/test_core_event_completions.py',
         'research_core_diagnostics.py', 'docs/CORE_EVENT_ACCOUNTING_PROTOCOL_20261029.md',
         'research_core_actions.py', 'docs/CORE_NORMALIZED_DATA_REPAIRS_20261029.md',
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
                    halt_valuation_assumptions=getattr(data, 'halt_marks', {}),
                    event_cache_files={'splits': f'splits-2022-06-30-{strategy.last_date}-v1.json.gz',
                                       'dividends': f'dividends-{START}-{strategy.last_date}-v1.json.gz'})
    daily = [dict(s, spy_nav=b['nav']) for s, b in zip(strategy.equity, benchmark.equity)]
    write_csv(folder / 'Momentum_core_daily.csv', daily)
    atomic_json(folder / 'diagnostics.json', describe(daily))
    write_csv(folder / 'Momentum_core_trades.csv', strategy.trades)
    write_csv(folder / 'Momentum_core_periods.csv', periods)
    atomic_json(folder / 'Momentum_core_targets.json', strategy.targets)
    atomic_json(folder / 'Momentum_core_state.json', strategy.to_dict())
    atomic_json(folder / 'Momentum_core_decision.json', decision)
    atomic_json(folder / 'experiment_facts.json', {'cash_actions': data.cash_actions, 'stock_actions': data.stock_actions,
                'distributions': getattr(data, 'distributions', []), 'halt_marks': getattr(data, 'halt_marks', {})})
    atomic_json(folder / 'checkpoint.json', {'strategy': strategy.to_dict(), 'benchmark': benchmark.to_dict()})
    return decision


def accounting_audit(cache, folder):
    previous = sys.argv
    try:
        sys.argv = ['audit_core_research_account.py', str(cache), str(folder)]
        with redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / 'audit_core_research_account.py'), run_name='__main__')
        return json.loads((folder / 'Momentum_core_accounting_audit.json').read_text())
    finally:
        sys.argv = previous


def payment_policy(data, delay):
    data.cash_actions, assumptions = policy_actions(data, delay)
    data.stock_actions = copy.deepcopy(data.source.stock_actions)
    for ticker, event in data.stock_actions.items():
        if event.get('cash_per_share') and delay is not None:
            i = bisect.bisect_left(data.days, event['effective_date'])
            if i + delay >= len(data.days):
                raise core.DataBlocked('Incomplete stock/cash payment calendar')
            event['pay_date'] = data.days[i + delay]
            assumptions.append({'ticker': ticker, 'assumed_pay_date': event['pay_date'], 'verified': False})
    return assumptions


def verify_control_events(data, folder):
    """Prove new events have no held shares/pending orders in saved controls."""
    state = json.loads((folder / 'checkpoint.json').read_text())['strategy']
    trades = state['trades']
    new_events = dict(STOCK_COMPLETIONS, **CASH_COMPLETIONS)
    for ticker, event in new_events.items():
        effective = event['effective_date']
        q = 0.
        for day in data.sessions:
            if day >= effective:
                break
            for e in data.source.splits_by_ticker.get(ticker, []):
                if e['execution_date'] == day:
                    q *= e['split_to'] / e['split_from']
            for t in trades:
                if t['date'] == day and t['ticker'] == ticker and t['side'] in ('BUY', 'SELL'):
                    q += t['quantity'] * (1 if t['side'] == 'BUY' else -1)
        if abs(q) > 1e-7:
            raise core.DataBlocked(f'New event touches saved control holdings {ticker}')
        previous = data.days[data.index[effective] - 1] if effective in data.index else None
        if any(s['date'] == previous and any(r['ticker'] == ticker for r in s['targets']) for s in state['targets']):
            raise core.DataBlocked(f'New event touches pending control order {ticker}')


def scan_holding_inputs(data, config):
    """Enumerate potential quote gaps without valuing a portfolio or performance.

    Missing buys remain cash and never create a replacement. Known conversions
    are applied on their effective dates. A missing held quote is reported, not
    filled. The scanner's affected sleeve is then untracked so other gaps can
    be found; actual replay remains blocked until every issue is resolved.
    """
    held, pending, previous, month = set(), None, False, ''
    gaps, selections, signals = [], [], []
    previous_day = None
    for day in data.sessions:
        data.set_day(day)
        prior_held = set(held)
        for ticker, event in data.cash_actions.items():
            if event['effective_date'] == day:
                held.discard(ticker)
        for ticker, event in data.stock_actions.items():
            if event['effective_date'] == day and ticker in held:
                held.remove(ticker)
                held.add(event['successor_ticker'])
        for e in getattr(data, 'distributions', []):
            if e['ex_date'] == day and e['parent'] in prior_held:
                held.add(e['recipient'])
        bars = data.bars(day)
        if pending is not None:
            desired = set()
            for ticker in pending:
                event = data.cash_actions.get(ticker) or data.stock_actions.get(ticker)
                if event and previous_day < event['effective_date'] <= day:
                    continue
                bar = bars.get(ticker)
                if ticker in held or (bar and core.number(bar[0]) is not None):
                    desired.add(ticker)
            for ticker in sorted(held - desired):
                if not bars.get(ticker) or core.number(bars[ticker][0]) is None:
                    gaps.append({'date': day, 'ticker': ticker, 'kind': 'MISSING_SELL_OPEN',
                                 'previous_session': previous_day})
            held = desired
        for ticker in sorted(held.copy()):
            if not bars.get(ticker) or core.number(bars[ticker][1]) is None:
                mark = getattr(data, 'halt_marks', {}).get(day)
                if mark and mark['ticker'] == ticker:
                    continue
                gaps.append({'date': day, 'ticker': ticker, 'kind': 'MISSING_HELD_CLOSE',
                             'previous_session': previous_day})
                held.remove(ticker)
        allowed = core.risk_on(data, day)
        pending = None
        if allowed and (month != day[:7] or not previous):
            rows, count = core.select_targets(data, day, config)
            selections.append({'date': day, 'targets': rows, 'eligible_count': count})
            signals.append({'date': day, 'risk_on': True, 'targets': rows, 'eligible_count': count})
            pending = {r['ticker'] for r in rows}
            month = day[:7]
        elif not allowed and (previous or previous_day is None):
            pending = set()
            signals.append({'date': day, 'risk_on': False, 'targets': [], 'eligible_count': 0})
        previous, previous_day = allowed, day
    return {'status': 'DATA_BLOCKED' if gaps else 'PASS', 'quote_gaps': gaps,
            'risk_on_selections': selections, 'all_signals': signals, 'performance_calculated': False,
            'scope': 'Potential held quote coverage, not whole-share execution or financial validation.'}


def render_report(register, path):
    rows = ['# Core risk-normalized ranking — 29 October 2026', '',
            'All observations are previously inspected development history. No live approval.', '',
            f"Study fingerprint: `{register['study_fingerprint']}`.", '',
            '| Phase | Payment policy | Cost/side | Candidate net % | Baseline net % | Candidate drawdown % | Failed gates |',
            '|---|---|---:|---:|---:|---:|---|']
    for a in register['attempts']:
        if a['status'] != 'COMPLETE':
            rows.append(f"| {a['phase']} | {a['policy']}/{a.get('halt_mark_policy', 'n/a')} | {a['cost']*10000:.0f} bp | {a['status']} | — | — | {a.get('error_type', '')} |")
            continue
        m = a['metrics']
        failed = ', '.join(g['gate'] for g in a['gates'] if not g['pass']) or 'none (PAPER_ONLY)'
        rows.append(f"| {a['phase']} | {a['policy']}/{a.get('halt_mark_policy', 'n/a')} | {a['cost']*10000:.0f} bp | {m['TotalReturn_pct']:.4f} | {a['control_metrics']['TotalReturn_pct']:.4f} | {m['DailyMaxDrawdown_pct']:.4f} | {failed} |")
    rows += ['', 'The historical boundary is 2026-09-01; extended rows retain the same account through 2026-10-28.',
             'Later-segment metrics are preserved separately in the JSON; neither segment is an untouched holdout.',
             'All five payment policies and both costs are retained. Assumed merger payment dates are unverified.',
             'Independent ranking/timing and accounting checks validate implementation, not independent market evidence.',
             'Vendor backfill, unverified payment dates, opening liquidity and actual execution costs remain limitations.',
             'The five existing gates and original Core paper identity are unchanged. No parameter is selected after results.', '']
    if register.get('unresolved_quote_gaps'):
        rows += ['## Input preflight — DATA_BLOCKED', '',
                 'No candidate performance was calculated in this run. Resolve the following facts before replay:', '']
        rows += [f"- {g['date']} {g['ticker']}: {g['kind']}" for g in register['unresolved_quote_gaps']]
    primary = next((a for a in register['attempts'] if a['phase'] == 'extension'
                    and a['status'] == 'COMPLETE' and a['delay'] == 5 and a['cost'] == .0015
                    and a['halt_mark_policy'] == 'last_quote'), None)
    if primary:
        rows += ['', '## Fixed display case: assumed 5-session payment, 15 bp/side, last-quote halt mark', '',
                 '| Account | Net % | Daily drawdown % | Daily Sharpe, RF=0 | Actual fees USD |',
                 '|---|---:|---:|---:|---:|']
        for label, m, fees in [('Normalized', primary['diagnostics']['full']['strategy'], primary['metrics']['ActualFees_USD']),
                               ('Core control', primary['control_diagnostics']['full']['strategy'], primary['control_metrics']['ActualFees_USD']),
                               ('SPY', primary['diagnostics']['full']['SPY'], primary['benchmark_fees_usd'])]:
            rows.append(f"| {label} | {m['return_pct']:.4f} | {m['max_drawdown_pct']:.4f} | {m['daily_sharpe_zero_rf']} | {fees:.2f} |")
        rows += ['', '| Calendar period | Normalized % | Core % | SPY % | Normalized drawdown % | Normalized Sharpe |',
                 '|---|---:|---:|---:|---:|---:|']
        for year, case in primary['diagnostics']['calendar_years'].items():
            m, spy = case['strategy'], case['SPY']
            control = primary['control_diagnostics']['calendar_years'][year]['strategy']
            rows.append(f"| {year} | {m['return_pct']:.4f} | {control['return_pct']:.4f} | {spy['return_pct']:.4f} | {m['max_drawdown_pct']:.4f} | {m['daily_sharpe_zero_rf']} |")
        rows += ['', 'The display case is not a selected approval scenario: all 40 marking/payment/cost/phase results remain above and in JSON.',
                 'No fresh out-of-sample history exists in these previously reviewed inputs. The later segment is reported separately, without relabelling it.', '']
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
            phase = 'historical' if a['phase'] == 'historical' else 'extended'
            folder = Path(args.controls_dir) / phase / a['name']
            with (folder / 'Momentum_core_trades.csv').open() as stream:
                symbols = {r['ticker'] for r in csv.DictReader(stream)}
            signals = json.loads((folder / 'Momentum_core_targets.json').read_text())
            symbols.update(r['ticker'] for s in signals for r in s['targets'])
            if symbols & EXTRA_CASH_ACTIONS.keys():
                raise core.DataBlocked('Supplemented event touches a saved baseline control')
    register = {'model': MODEL, 'study_fingerprint': study, 'core_fingerprint': source_fingerprint(),
                'frozen_input_manifest_fingerprint': manifest_hash,
                'input_files_verified': 1001, 'expected_attempts': 40,
                'supplemental_cash_actions': EXTRA_CASH_ACTIONS,
                'saved_control_supplement_isolation': 'PASS',
                'evidence_class': 'DEVELOPMENT_RESEARCH', 'certified_untouched_holdout': False,
                'live_approved': False, 'broker_orders_enabled': False, 'attempts': [],
                'all_attempts_completed': False, 'controls_reused_without_rerun': 20}
    atomic_json(register_path, register)
    checkpoints = {}
    audit_memo = {}
    with candidate_selection():
        full_data = complete_data(supplement(make_data(args.cache_dir, EXTENSION_END, True)))
        for a in expected['cases']:
            if a['name'].startswith('baseline_'):
                phase_name = 'historical' if a['phase'] == 'historical' else 'extended'
                verify_control_events(full_data, Path(args.controls_dir) / phase_name / a['name'])
        scan = scan_holding_inputs(full_data, replace(core.CONFIG, model=MODEL))
        atomic_json(output / 'holding_input_preflight.json', scan)
        selection_audit = audit_targets(full_data, replace(core.CONFIG, model=MODEL), scan['all_signals'], memo=audit_memo)
        atomic_json(output / 'preflight_selection_audit.json', selection_audit)
        register['preflight_selection_audit'] = selection_audit
        register['holding_input_preflight_status'] = scan['status']
        register['unresolved_quote_gaps'] = scan['quote_gaps']
        atomic_json(register_path, register)
        render_report(register, output / 'report.md')
        if scan['quote_gaps']:
            for gap in scan['quote_gaps']:
                print('PREFLIGHT_GAP ' + json.dumps(gap), flush=True)
            raise core.DataBlocked('Holding-input preflight found unresolved quotes; no performance calculated')
        for mark_policy in ('last_quote', 'offer_value'):
            for phase, end in (('historical', CUTOFF), ('extension', EXTENSION_END)):
                data = full_data if phase == 'extension' else supplement(make_data(args.cache_dir, end, True))
                data = complete_data(data, mark_policy)
                for delay in DELAYS:
                    assumptions = payment_policy(data, delay)
                    policy = 'locked' if delay is None else f'assumed_{delay}'
                    for cost in (.0015, .003):
                        name = f'normalized_{policy}_{round(cost * 10000)}bps_{mark_policy}'
                        control = controls[(phase, f'baseline_{policy}_{round(cost * 10000)}bps')]
                        attempt = dict(phase=phase, name=name, policy=policy, delay=delay, cost=cost,
                                       payment_assumptions=assumptions, halt_mark_policy=mark_policy, status='RUNNING',
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
                            s, b, result, periods = replay(data, config, cls=ResearchLedger, checkpoint=checkpoint, sessions=sessions)
                            result['DailySharpe_zero_rf'] = performance(s.equity)['daily_sharpe_zero_rf']
                            if checkpoint:
                                for field in ('equity', 'trades', 'targets'):
                                    assert getattr(s, field)[:len(checkpoint[0][field])] == checkpoint[0][field]
                                assert b.equity[:len(checkpoint[1]['equity'])] == checkpoint[1]['equity']
                            folder = output / phase / name
                            decision = save_case(folder, data, config, s, b, result, periods, attempt, study)
                            accounting = accounting_audit(args.cache_dir, folder)
                            selection = audit_targets(data, config, s.targets, s.trades, audit_memo)
                            atomic_json(folder / 'Momentum_core_selection_audit.json', selection)
                            control_phase = 'historical' if phase == 'historical' else 'extended'
                            control_folder = Path(args.controls_dir) / control_phase / f'baseline_{policy}_{round(cost*10000)}bps'
                            with (control_folder / 'Momentum_core_daily.csv').open() as stream:
                                control_diagnostics = describe(list(csv.DictReader(stream)))
                            attempt.update(status='COMPLETE', decision_status=decision['status'], metrics=result,
                                           benchmark_fees_usd=b.fees,
                                           diagnostics=describe([dict(x, spy_nav=y['nav']) for x,y in zip(s.equity,b.equity)]),
                                           control_diagnostics=control_diagnostics,
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
                            print('BLOCKED ' + phase + ' ' + name + ': ' + str(exc), flush=True)
                        except Exception as exc:
                            attempt.update(status='VALIDATION_ERROR', error_type=type(exc).__name__, error=str(exc))
                            raise
                        finally:
                            atomic_json(register_path, register)
                            render_report(register, output / 'report.md')
    assert fingerprint() == study
    verify_inputs(args.cache_dir, args.manifest)
    register['all_attempts_completed'] = (len(register['attempts']) == 40
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
