"""Frozen stop10 experiment: exact baseline, all scenarios, then new segment.

Results never approve real-money orders. Run once into a new output directory.
"""
from __future__ import annotations

import argparse
import bisect
import copy
import functools
import hashlib
import io
import json
import logging
import os
import re
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from datetime import date, timedelta
from pathlib import Path
import runpy
import socket
import sys

import momentum_core as core
from momentum_core_data import CoreData, atomic_json
from momentum_master_v3 import PolygonClient
from research_core_stop import MODEL, StopLedger
from run_momentum_core import source_fingerprint, write_csv

ROOT = Path(__file__).resolve().parent
START, CUTOFF, EXTENSION_END = '2024-01-01', '2026-09-01', '2026-10-28'
DELAYS = (None, 0, 1, 5, 20)
STUDY_FILES = ('research_core_stop.py', 'run_core_risk_research.py',
               'docs/CORE_STOP10_PROTOCOL_20261029.md')


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def study_fingerprint():
    return sha({'original_source': source_fingerprint(),
                'study_files': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in STUDY_FILES}})


class DailyEvents:
    """Only bookkeeping events are indexed; signal split history stays complete."""
    def __init__(self, source):
        self.source = source
        self.splits_by_day, self.dividends_by_day = {}, {}
        for event in source.splits:
            self.splits_by_day.setdefault(event['execution_date'], []).append(event)
        for event in source.dividends:
            self.dividends_by_day.setdefault(event['ex_dividend_date'], []).append(event)
        self.splits, self.dividends = [], []
        self.cash_actions = copy.deepcopy(source.cash_actions)

    def __getattr__(self, name):
        return getattr(self.source, name)

    def set_day(self, day):
        self.splits = self.splits_by_day.get(day, [])
        self.dividends = self.dividends_by_day.get(day, [])


def policy_actions(data, delay):
    actions = copy.deepcopy(data.source.cash_actions)
    assumptions = []
    if delay is not None:
        for ticker, event in actions.items():
            if event.get('pay_date'):
                continue
            i = bisect.bisect_left(data.days, event['effective_date'])
            if i >= len(data.days) or data.days[i] != event['effective_date'] or i + delay >= len(data.days):
                raise core.DataBlocked(f'Incomplete assumed payment calendar {ticker}')
            event['pay_date'] = data.days[i + delay]
            assumptions.append({'ticker': ticker, 'assumed_pay_date': event['pay_date'], 'verified': False})
    return actions, assumptions


def make_data(cache, end, offline):
    key = os.getenv('POLYGON_API_KEY')
    if not offline and not key:
        raise core.DataBlocked('POLYGON_API_KEY missing for new research segment')
    data = CoreData(None if offline else PolygonClient(key), START, end, cache, offline=offline)
    data.bars = functools.lru_cache(maxsize=None)(data.bars.__wrapped__.__get__(data, CoreData))
    # Preserve the fixed complete input window before any accounting failure.
    for day in data.days[data.index[data.sessions[0]] - 252:]:
        data.bars(day)
    return DailyEvents(data)


def replay(data, config, cls=core.Ledger, checkpoint=None, sessions=None):
    strategy = cls(**copy.deepcopy(checkpoint[0])) if checkpoint else cls(cash=config.initial_cash)
    benchmark = core.Ledger(**copy.deepcopy(checkpoint[1])) if checkpoint else core.Ledger(cash=config.initial_cash)
    if not checkpoint:
        strategy.first_is_month_boundary = data.first_is_month_boundary()
    for day in sessions if sessions is not None else data.sessions:
        data.set_day(day)
        benchmark.step(data, day, config, benchmark=True)
        strategy.step(data, day, config)
    result, periods = core.metrics(strategy, benchmark)
    return strategy, benchmark, result, periods


def exports(folder, data, strategy, benchmark, result, periods, config, metadata, end):
    folder.mkdir(parents=True, exist_ok=True)
    checks = core.gates(result)
    decision = dict(metadata, start=START, end=end,
                    model=MODEL if isinstance(strategy, StopLedger) else core.MODEL,
                    status='PAPER_ONLY' if all(g['pass'] for g in checks) else 'NO_GO',
                    metrics=result, gates=checks, config=asdict(config),
                    source_fingerprint=source_fingerprint(), study_fingerprint=study_fingerprint(),
                    input_fingerprint=data.input_fingerprint(), live_approved=False,
                    broker_orders_enabled=False, evidence_class='DEVELOPMENT_RESEARCH',
                    event_cache_files={'splits': f'splits-2022-06-30-{end}-v1.json.gz',
                                       'dividends': f'dividends-{START}-{end}-v1.json.gz'},
                    unresolved_cash_claims=strategy.receivables)
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


def audit(cache, folder):
    old_args = sys.argv
    try:
        sys.argv = ['audit_core_risk_research.py', str(cache), str(folder)]
        with redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / 'audit_core_risk_research.py'), run_name='__main__')
        return json.loads((folder / 'Momentum_core_accounting_audit.json').read_text())
    finally:
        sys.argv = old_args


def extension_metrics(strategy, benchmark):
    first = next(i for i, row in enumerate(strategy.equity) if row['date'] == CUTOFF)
    s, b = core.Ledger(), core.Ledger()
    s.equity, b.equity = strategy.equity[first:], benchmark.equity[first:]
    s.first_is_month_boundary = True
    result, _ = core.metrics(s, b)
    return dict(result, sessions_after_cutoff=len(s.equity) - 1,
                evidence_class='POST_FREEZE_HISTORICAL_EXTENSION',
                certified_untouched_holdout=False, forward_paper=False)


def run(args):
    output, baseline = Path(args.output_dir), Path(args.baseline_dir)
    if (output / 'attempts.json').exists():
        raise ValueError('Preserve prior attempts; use a fresh output directory')
    output.mkdir(parents=True, exist_ok=True)
    original = json.loads((baseline / 'Momentum_core_decision.json').read_text())
    assert source_fingerprint() == original['source_fingerprint'], 'Core source differs from original experiment'
    original_targets = json.loads((baseline / 'Momentum_core_targets.json').read_text())
    saved_signals = {row['date']: row for row in original_targets if row['risk_on']}
    original_select, original_risk = core.select_targets, core.risk_on
    @functools.lru_cache(maxsize=None)
    def cached_select(data, day, config):
        if day in saved_signals and all(getattr(config, n) == getattr(core.CONFIG, n)
                for n in ('positions', 'min_price', 'min_adv', 'vol_returns', 'max_weight')):
            data.universe(day)  # Track and verify the same dated input hash.
            row = saved_signals[day]
            return copy.deepcopy(row['targets']), row['eligible_count']
        return original_select(data, day, config)
    core.select_targets = cached_select
    core.risk_on = functools.lru_cache(maxsize=None)(original_risk)
    register = {'study_fingerprint': study_fingerprint(), 'original_source_fingerprint': source_fingerprint(),
                'source_commit': os.getenv('GITHUB_SHA'), 'fixed_delays': list(DELAYS),
                'fixed_stop_fraction': .10, 'live_approved': False, 'broker_orders_enabled': False,
                'original_targets_sha256': hashlib.sha256((baseline / 'Momentum_core_targets.json').read_bytes()).hexdigest(),
                'attempts': []}
    path = output / 'attempts.json'
    atomic_json(path, register)
    data = make_data(args.cache_dir, CUTOFF, True)
    expected_cases = json.loads((ROOT / 'docs/CORE_CASH_TIMING_RESULTS_20261028.json').read_text())
    expected = {x['name']: x for x in expected_cases['attempts']}
    checkpoints = {}
    for family, cls in (('baseline', core.Ledger), ('stop10', StopLedger)):
        for delay in DELAYS:
            data.cash_actions, assumptions = policy_actions(data, delay)
            for cost in (.0015, .003):
                policy = 'locked' if delay is None else f'assumed_{delay}'
                name = f'{family}_{policy}_{round(cost * 10000)}bps'
                config = replace(core.CONFIG, one_way_cost=cost)
                attempt = {'phase': 'historical', 'name': name, 'family': family,
                           'delay': delay, 'cost': cost, 'payment_assumptions': assumptions, 'status': 'RUNNING'}
                register['attempts'].append(attempt)
                atomic_json(path, register)
                print('START historical ' + name, flush=True)
                try:
                    s, b, result, periods = replay(data, config, cls)
                    folder = output / 'historical' / name
                    d = exports(folder, data, s, b, result, periods, config, attempt, CUTOFF)
                    if family == 'baseline':
                        old_label = 'baseline' if delay is None else f'assumed_{delay}_sessions'
                        assert result == expected[f'{old_label}_{round(cost*10000)}bps']['metrics']
                        assert data.input_fingerprint() == original['input_fingerprint']
                        if delay is None:
                            target = original['metrics'] if cost == .0015 else original['double_cost_metrics']
                            assert result == target
                            if cost == .0015:
                                for suffix in ('daily.csv', 'trades.csv', 'periods.csv', 'targets.json', 'state.json'):
                                    filename = 'Momentum_core_' + suffix
                                    assert (folder / filename).read_bytes() == (baseline / filename).read_bytes(), filename
                    a = audit(args.cache_dir, folder)
                    checkpoints[name] = (s.to_dict(), b.to_dict(), cls, config, delay)
                    attempt.update(status='COMPLETE', decision_status=d['status'], metrics=result,
                                   gates=d['gates'], accounting_audit=a['status'], max_nav_error_usd=a['max_nav_error_usd'],
                                   stop_signals=len(getattr(s, 'stop_signals', [])), input_fingerprint=data.input_fingerprint())
                    print('DONE historical ' + name + ' ' + json.dumps(result), flush=True)
                except core.DataBlocked as exc:
                    attempt.update(status='DATA_BLOCKED', error=str(exc))
                    print('BLOCKED historical ' + name + ': ' + str(exc), flush=True)
                atomic_json(path, register)
    if not args.historical_only:
        if args.end != EXTENSION_END:
            raise ValueError('Extension end is frozen at ' + EXTENSION_END)
        full = make_data(args.cache_dir, args.end, args.offline)
        new_days = [d for d in full.sessions if d > CUTOFF]
        if not new_days or new_days[-1] != args.end:
            raise core.DataBlocked('Incomplete fixed extension calendar')
        for name, (s0, b0, cls, config, delay) in checkpoints.items():
            full.cash_actions, assumptions = policy_actions(full, delay)
            attempt = {'phase': 'extension', 'name': name, 'delay': delay, 'cost': config.one_way_cost,
                       'payment_assumptions': assumptions, 'status': 'RUNNING',
                       'prefix_input_fingerprint': original['input_fingerprint']}
            register['attempts'].append(attempt)
            atomic_json(path, register)
            print('START extension ' + name, flush=True)
            try:
                s, b, result, periods = replay(full, config, cls, (s0, b0), new_days)
                assert s.equity[:len(s0['equity'])] == s0['equity']
                assert s.trades[:len(s0['trades'])] == s0['trades']
                folder = output / 'extended' / name
                d = exports(folder, full, s, b, result, periods, config, attempt, args.end)
                a = audit(args.cache_dir, folder)
                attempt.update(status='COMPLETE', metrics=result, gates=d['gates'],
                               decision_status=d['status'], extension_metrics=extension_metrics(s, b),
                               accounting_audit=a['status'], max_nav_error_usd=a['max_nav_error_usd'],
                               input_fingerprint=full.input_fingerprint())
                print('DONE extension ' + name + ' ' + json.dumps(attempt['extension_metrics']), flush=True)
            except core.DataBlocked as exc:
                attempt.update(status='DATA_BLOCKED', error=str(exc))
                print('BLOCKED extension ' + name + ': ' + str(exc), flush=True)
            atomic_json(path, register)
    assert study_fingerprint() == register['study_fingerprint']
    register['batch_completed'] = True
    register['all_attempts_completed'] = all(x['status'] == 'COMPLETE' for x in register['attempts'])
    atomic_json(path, register)
    core.select_targets, core.risk_on = original_select, original_risk
    return register


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', required=True)
    parser.add_argument('--baseline-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--end', default=EXTENSION_END)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--historical-only', action='store_true')
    options = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    if options.offline or options.historical_only:
        def blocked(*args, **kwargs):
            raise RuntimeError('Network forbidden in offline study')
        socket.socket.connect = blocked
        socket.create_connection = blocked
    try:
        result = run(options)
    except Exception as exc:
        # API exceptions can contain credential-bearing request URLs. Never
        # export a raw traceback/URL into a public research log.
        message = re.sub(r'(?i)(apiKey=)[^&\s]+', r'\1[REDACTED]', str(exc))
        secret = os.getenv('POLYGON_API_KEY')
        if secret:
            message = message.replace(secret, '[REDACTED]')
        folder = Path(options.output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        error = {'status': 'STUDY_BLOCKED', 'error': message, 'error_type': type(exc).__name__,
                 'live_approved': False, 'broker_orders_enabled': False}
        atomic_json(folder / 'study_error.json', error)
        print(json.dumps(error), flush=True)
        raise SystemExit(1)
    raise SystemExit(0 if result['all_attempts_completed'] else 1)
