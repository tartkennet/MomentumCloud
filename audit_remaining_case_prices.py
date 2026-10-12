"""Inventory fixed-day observations for all remaining documentary cases.

This does not infer that a missing quote is a corporate action, change holding
windows, approve issuer identity, or compute the eligible-universe return.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def main():
    root = Path(__file__).parent
    full = json.loads((root / 'classification/verified_ticker_histories.json').read_text())
    for file in sorted((root / 'universe_evidence').glob('histories*.json')):
        for ticker, bases in json.loads(file.read_text()).items():
            parsed = {}
            for name, key in [('raw', 'false'), ('adjusted', 'true')]:
                if 'error_type' in bases[key] or bases[key].get('next_url'):
                    raise RuntimeError(f'Incomplete individual source: {ticker} {name}')
                parsed[name] = {
                    datetime.fromtimestamp(bar['t'] / 1000, timezone.utc).date().isoformat(): bar
                    for bar in bases[key].get('results', [])
                }
            full[ticker] = parsed
    ledger = json.loads((root / 'audit_evidence/universe_remaining_ledger.json').read_text())
    periods = pd.read_csv(root / 'evidence/selection/Momentum_verified_gap_model/'
                          'momentum_selection_only_results.csv').set_index('SignalDate')
    output = []
    for case in ledger:
        if case['reviewed_action_record_available']:
            continue
        period = periods.loc[case['signal']]
        if case['issue'].startswith('entry '):
            target = str(period.EntryDate)
        elif case['issue'].startswith('exit '):
            target = str(period.ExitDate)
        else:
            raise ValueError('Unknown case issue: ' + case['issue'])
        bases = {}
        for basis in ['raw', 'adjusted']:
            history = full.get(case['ticker'], {}).get(basis, {})
            bases[basis] = {'bars': len(history), 'first': min(history) if history else None,
                            'last': max(history) if history else None,
                            'fixed_target_observed': target in history}
        status = ('SCHEDULED_PAIRED_BAR_OBSERVED_NOT_EXECUTION_APPROVAL'
                  if all(bases[basis]['fixed_target_observed'] for basis in bases)
                  else 'SCHEDULED_PAIR_MISSING')
        output.append({**case, 'fixed_target_date': target,
                       'individual_history_bases': bases, 'price_observation_status': status})
    report = {'status': 'COMPLETE_INVENTORY_ONLY', 'cases': len(output),
              'status_counts': dict(Counter(row['price_observation_status'] for row in output)),
              'records': output}
    target = root / 'audit_evidence/remaining_cases_price_inventory_20261012.json'
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'}))


if __name__ == '__main__':
    main()
