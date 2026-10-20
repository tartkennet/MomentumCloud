"""Run the fixed restored audit locally and retain every stage before proceeding."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def verify(output, source_head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    summary = {'status': 'RUNNING', 'source_head': source_head,
               'started_utc': datetime.now(timezone.utc).isoformat(), 'stages': [],
               'packages': {name: importlib.metadata.version(name) for name in
                            ['pandas', 'numpy', 'pyarrow', 'requests', 'openpyxl']}}
    source_files = [path for path in ROOT.glob('*.py') if path.is_file()]
    source_files += list((ROOT / 'verified_exit_settlements.py').glob('*.py'))
    source_files += list((ROOT / 'tests').glob('*.py'))
    summary['source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(source_files)}
    state_path = output / 'batch_summary.json'

    def save():
        state_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')

    def run(name, arguments, environment=None):
        summary['current_stage'] = name
        save()
        print('START', name, flush=True)
        with (output / (name + '.log')).open('w') as log:
            result = subprocess.run([sys.executable, *arguments], cwd=ROOT,
                                    env={**os.environ, **(environment or {})},
                                    stdout=log, stderr=subprocess.STDOUT)
        summary['stages'].append({'name': name, 'returncode': result.returncode})
        save()
        if result.returncode:
            raise RuntimeError(name + ' failed; inspect retained log')
        print('COMPLETE', name, flush=True)

    try:
        shutil.copyfile(ROOT / 'audit_evidence/recovery_validation_20261019.json', output / 'input_recovery.json')
        run('regression_tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
        test_log = (output / 'regression_tests.log').read_text()
        summary['regression_tests'] = int(re.search(r'Ran (\d+) tests', test_log).group(1))
        run('archive_reverification', ['reverify_selection_archive.py', 'evidence/selection'])
        summary['archive_reverification'] = json.loads((output / 'archive_reverification.log').read_text())
        run('action_basis_preflight', ['audit_action_basis_batch.py', '--requests',
            'audit_evidence/basis_requests_recovered_20261014.json', '--output', str(output / 'action_basis_preflight.json')])
        preflight = json.loads((output / 'action_basis_preflight.json').read_text())
        summary['preflight'] = {key: value for key, value in preflight.items() if key != 'records'}
        if preflight['missing_pairs']:
            raise RuntimeError('Missing paired observations; retained full batch inventory')

        run('selection_model', ['replay_verified_audit_offline.py'], {'SCENARIO': 'momentum_selection_only'})
        model_prefix = 'momentum_selection_only'
        for suffix in ['positions.csv', 'results.csv', 'model_result.json']:
            shutil.copyfile(ROOT / 'Momentum_verified_gap_model' / (model_prefix + '_' + suffix), output / (model_prefix + '_' + suffix))
        import numpy as np
        import pandas as pd
        reference = ROOT / 'evidence/selection/Momentum_verified_gap_model'
        actual = pd.read_csv(output / (model_prefix + '_positions.csv')).set_index(['SignalDate', 'Ticker']).sort_index()
        archived = pd.read_csv(reference / (model_prefix + '_positions.csv')).set_index(['SignalDate', 'Ticker']).sort_index()
        if not actual.index.equals(archived.index):
            raise AssertionError('Fresh selection keys differ from archived fixed selection')
        for field in ['SignalPrice_USD', 'EntryPrice_USD', 'ExitPrice_USD', 'EntryDate', 'ExitDate']:
            if not np.array_equal(actual[field].to_numpy(), archived[field].to_numpy()):
                raise AssertionError('Fresh archived selection mismatch: ' + field)
        fresh = json.loads((output / (model_prefix + '_model_result.json')).read_text())
        old = json.loads((reference / (model_prefix + '_model_result.json')).read_text())
        for field in ['TotalReturn_pct', 'DailyMaxDrawdown_pct']:
            if not np.isclose(fresh['metrics'][field], old['metrics'][field], atol=1e-9, rtol=0):
                raise AssertionError('Fresh model metric differs: ' + field)
        summary['selection'] = {'status': 'PASS_FRESH_REPLAY_AFTER_COMPLETE_GOLD_AND_NCR_BATCH',
            'positions': len(actual), 'tickers': int(actual.index.get_level_values('Ticker').nunique()),
            'periods': int(actual.index.get_level_values('SignalDate').nunique()),
            'exact_position_keys_prices_dates': True, 'metrics': fresh['metrics'],
            'spy_matched_cost_pct': fresh['spy_matched_monthly_fixed_cost_return_pct'],
            'checks': fresh['checks']}
        save()

        run('universe_diagnostic', ['run_universe_diagnostic_batch.py', '--output', str(output / 'universe_diagnostic.json')])
        summary['universe'] = json.loads((output / 'universe_diagnostic.json').read_text())
        summary['status'] = 'COMPLETE_VERIFICATION_UNIVERSE_BLOCKED' if summary['universe']['status'] == 'BLOCKED_NO_VALID_UNIVERSE_RETURN' else 'COMPLETE_REQUIRES_UNIVERSE_REVIEW'
        summary['decision'] = 'NO_GO'
        summary['limitation'] = 'No valid universe return or ranking benefit while executions remain unresolved; no actual fill approval.'
    except Exception as error:
        summary['status'] = 'FAILED_RETAINED_STAGE_OUTPUTS'
        summary['error'] = str(error)
        raise
    finally:
        summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
        summary.pop('current_stage', None)
        save()
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(output.iterdir()) if path.is_file() and path.name != 'manifest.json'}
        (output / 'manifest.json').write_text(json.dumps({'files': hashes}, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-head', required=True)
    args = parser.parse_args()
    verify(args.output_dir, args.source_head)
