"""Bounded, offline cash-payment diagnostic. Never changes production decisions."""
from __future__ import annotations

import bisect
import copy
import functools
import hashlib
import io
import json
import logging
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from pathlib import Path
import runpy
import socket
import sys

import backtest_momentum_v3 as facts
import momentum_core as core
from momentum_core_data import CoreData, atomic_json
from run_momentum_core import replay, source_fingerprint, write_csv

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
CACHE = WORK / 'final_research/snapshot/cache'
ORIGINAL = WORK / 'final_research/evidence/core_results'
OUTPUT = ROOT / 'cash_timing_results'
DELAYS = (None, 0, 1, 5, 20)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def forbid_network(*args, **kwargs):
    raise RuntimeError('Network is forbidden in this saved-input experiment')


def main():
    socket.socket.connect = forbid_network
    socket.create_connection = forbid_network
    OUTPUT.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    protocol = ROOT / 'docs/CORE_CASH_TIMING_EXPERIMENT_20261028.md'
    protocol_hash = hashlib.sha256(protocol.read_bytes()).hexdigest()
    original = json.loads((ORIGINAL / 'Momentum_core_decision.json').read_text())
    assert source_fingerprint() == original['source_fingerprint']
    # These functions depend on date, market inputs and frozen configuration,
    # never on holdings/cash. Reuse does not reuse any simulated account state.
    core.risk_on = functools.lru_cache(maxsize=None)(core.risk_on)
    core.select_targets = functools.lru_cache(maxsize=None)(core.select_targets)
    data = CoreData(None, '2024-01-01', '2026-09-01', CACHE, offline=True)
    # Keep all immutable market inputs hot across the fixed batch.
    data.bars = functools.lru_cache(maxsize=None)(data.bars.__wrapped__.__get__(data, CoreData))
    known = copy.deepcopy(facts.CASH_CORPORATE_ACTIONS)
    register = {'protocol_sha256': protocol_hash,
                'model_source_fingerprint': original['source_fingerprint'],
                'baseline_input_fingerprint': original['input_fingerprint'],
                'source_commit': original['source_commit'],
                'evidence_class': 'DEVELOPMENT_SENSITIVITY',
                'live_approved': False, 'broker_orders_enabled': False,
                'payment_dates_verified': False,
                'selection_or_gates_changed': False,
                'delays_fixed_before_run': list(DELAYS), 'attempts': []}
    atomic_json(OUTPUT / 'attempts.json', register)
    for delay in DELAYS:
        label = 'baseline' if delay is None else f'assumed_{delay}_sessions'
        actions = copy.deepcopy(known)
        assumptions = []
        if delay is not None:
            for ticker, action in actions.items():
                if action.get('pay_date'):
                    continue
                i = bisect.bisect_left(data.days, action['effective_date'])
                j = i + delay
                if i == len(data.days) or data.days[i] != action['effective_date'] or j >= len(data.days):
                    raise RuntimeError(f'Unavailable assumed event calendar: {ticker}')
                action['pay_date'] = data.days[j]
                assumptions.append({'ticker': ticker, 'effective_date': action['effective_date'],
                                    'assumed_pay_date': data.days[j], 'verified': False})
        data.cash_actions = actions
        facts.CASH_CORPORATE_ACTIONS = actions
        for cost in (0.0015, 0.003):
            name = f'{label}_{round(cost * 10000)}bps'
            folder = OUTPUT / name
            folder.mkdir(exist_ok=True)
            config = replace(core.CONFIG, one_way_cost=cost)
            attempt = {'name': name, 'assumed_delay_sessions': delay,
                       'one_way_cost': cost, 'payment_assumptions': assumptions,
                       'status': 'RUNNING', 'live_approved': False,
                       'experiment_fingerprint': digest({'source': original['source_fingerprint'],
                            'inputs': original['input_fingerprint'], 'actions': actions,
                            'config': asdict(config), 'protocol': protocol_hash})}
            register['attempts'].append(attempt)
            atomic_json(OUTPUT / 'attempts.json', register)
            print(f'START {name}', flush=True)
            try:
                strategy, benchmark, result, periods = replay(data, config)
                attempt.update(status='COMPLETE', metrics=result, gates=core.gates(result),
                               input_fingerprint=data.input_fingerprint(),
                               all_economic_gates_pass=all(g['pass'] for g in core.gates(result)),
                               unresolved_cash_claims=strategy.receivables)
                if delay is None:
                    expected = original['metrics'] if cost == 0.0015 else original['double_cost_metrics']
                    assert result == expected, (result, expected)
                    assert data.input_fingerprint() == original['input_fingerprint']
                write_csv(folder / 'Momentum_core_daily.csv', [dict(row, spy_nav=spy['nav'])
                    for row, spy in zip(strategy.equity, benchmark.equity)])
                write_csv(folder / 'Momentum_core_trades.csv', strategy.trades)
                write_csv(folder / 'Momentum_core_periods.csv', periods)
                atomic_json(folder / 'Momentum_core_targets.json', strategy.targets)
                atomic_json(folder / 'Momentum_core_state.json', strategy.to_dict())
                audit_decision = dict(attempt, model=core.MODEL,
                        source_fingerprint=original['source_fingerprint'],
                        config=asdict(config), source_commit=original['source_commit'])
                atomic_json(folder / 'Momentum_core_decision.json', audit_decision)
                if delay is None and cost == 0.0015:
                    matches = {}
                    for suffix in ('daily.csv','trades.csv','periods.csv','targets.json','state.json'):
                        filename = 'Momentum_core_' + suffix
                        a, b = (folder / filename).read_bytes(), (ORIGINAL / filename).read_bytes()
                        assert a == b, f'Baseline differs: {filename}'
                        matches[filename] = hashlib.sha256(a).hexdigest()
                    attempt['baseline_byte_parity'] = matches
                if cost == 0.0015:
                    previous_argv = sys.argv
                    try:
                        sys.argv = ['audit_momentum_core.py', str(CACHE), str(folder)]
                        with redirect_stdout(io.StringIO()):
                            runpy.run_path(str(ROOT / 'audit_momentum_core.py'), run_name='__main__')
                        attempt['independent_accounting_audit'] = json.loads(
                            (folder / 'Momentum_core_accounting_audit.json').read_text())['status']
                    finally:
                        sys.argv = previous_argv
                print('DONE ' + name + ' ' + json.dumps(result), flush=True)
            except core.DataBlocked as exc:
                attempt.update(status='DATA_BLOCKED', error=str(exc))
                print('BLOCKED ' + name + ': ' + str(exc), flush=True)
            except Exception as exc:
                attempt.update(status='VERIFICATION_FAILED', error=str(exc), error_type=type(exc).__name__)
                atomic_json(OUTPUT / 'attempts.json', register)
                raise
            atomic_json(OUTPUT / 'attempts.json', register)
    facts.CASH_CORPORATE_ACTIONS = known
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == protocol_hash
    register['batch_completed'] = True
    atomic_json(OUTPUT / 'attempts.json', register)


if __name__ == '__main__':
    main()
