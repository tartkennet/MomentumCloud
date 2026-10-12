"""Inventory a whole quote batch from frozen observations, without model reruns.

The request list is a broad action-basis preflight, not a list of approved
executions or necessarily of holdings in the final eligible universe.
Missing observations remain missing; no prices or adjustment factors are inferred.
"""
import json
import math
from pathlib import Path
from datetime import datetime, timezone


def inspect_pair(request, get):
    ticker, day = request['ticker'], request['day']
    path = f'/v2/aggs/ticker/{ticker}/range/1/day/{day}/{day}'
    observations, missing = {}, []
    for name, adjusted in [('adjusted', 'true'), ('raw', 'false')]:
        params = {'adjusted': adjusted, 'sort': 'asc', 'limit': 10}
        try:
            payload = get(None, path, params)
        except RuntimeError as exc:
            if not str(exc).startswith(('OFFLINE_REQUEST_MISSING ', 'OFFLINE_HISTORY_ERROR ')):
                raise
            missing.append({'path': path, 'params': params, 'reason': str(exc)})
            continue
        bars = payload.get('results', [])
        fields = ['o', 'h', 'l', 'c', 'v', 't']
        if len(bars) != 1 or any(field not in bars[0] for field in fields):
            missing.append({'path': path, 'params': params,
                            'reason': 'NO_SINGLE_COMPLETE_OBSERVED_BAR'})
            continue
        bar = {field: bars[0][field] for field in fields}
        if any(not math.isfinite(float(bar[field])) for field in fields):
            raise ValueError(f'Non-finite observed bar: {ticker} {day} {name}')
        if any(float(bar[field]) <= 0 for field in fields[:4]):
            raise ValueError(f'Non-positive observed price: {ticker} {day} {name}')
        observed_day = datetime.fromtimestamp(float(bar['t']) / 1000, timezone.utc).date().isoformat()
        if observed_day != day:
            missing.append({'path': path, 'params': params,
                            'reason': 'OBSERVATION_DATE_DOES_NOT_MATCH_REQUEST'})
            continue
        observations[name] = [bar]
    return {**request, 'status': 'OBSERVED_PAIR_ONLY' if not missing else 'MISSING_OBSERVED_PAIR',
            'observations': observations, 'missing_requests': missing}


def main():
    from replay_verified_audit_offline import offline_get
    root = Path(__file__).parent
    requests = json.loads((root / 'audit_evidence/basis_requests_bulk.json').read_text())
    records = [inspect_pair(request, offline_get) for request in requests]
    missing = [record for record in records if record['missing_requests']]
    output = {
        'status': 'COMPLETE_PREFLIGHT_NOT_MODEL_EXECUTION',
        'requested_pairs': len(records),
        'observed_pairs': len(records) - len(missing),
        'missing_pairs': len(missing),
        'missing_individual_requests': sum(len(record['missing_requests']) for record in missing),
        'full_universe_complete': False,
        'records': records,
    }
    target = root / 'audit_evidence/action_basis_preflight_20261012.json'
    target.write_text(json.dumps(output, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in output.items() if key != 'records'}), flush=True)


if __name__ == '__main__':
    main()
