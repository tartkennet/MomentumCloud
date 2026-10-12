"""Collect all unavailable action bases in one fixed-universe diagnostic.

An unavailable basis makes that execution unresolved. No substitute price or
partial-universe return is published. Unexpected errors still abort the run.
"""
import json
import os
from pathlib import Path


def evidence_error(error):
    return str(error).startswith((
        'OFFLINE_REQUEST_MISSING ', 'OFFLINE_HISTORY_ERROR ',
        'Missing paired action basis:', 'Action basis disagrees with execution cache:',
        'No original pre-action basis:', 'No successor action basis:',
    ))


def main():
    os.environ['SCENARIO'] = 'eligible_universe_equal_weight'
    import replay_verified_audit_offline as replay
    import audit_action_price_install as installation
    target = Path('audit_evidence/universe_diagnostic_batch_20261012.json')
    original_install = installation.install_compatible_action_prices
    issues = []

    def collect_install(engine, paired_factor):
        original_install(engine, paired_factor)
        resolver = engine.resolve_exit_execution

        def collect(cache, days, ticker, target_day, entry, latest):
            try:
                return resolver(cache, days, ticker, target_day, entry, latest)
            except RuntimeError as error:
                if not evidence_error(error):
                    raise
                issues.append({'ticker': ticker, 'target_day': target_day,
                               'entry_day': entry, 'reason': str(error)})
                # Every completed collection pass is a recoverable checkpoint.
                target.write_text(json.dumps({'status': 'RUNNING_DIAGNOSTIC_ONLY',
                                             'basis_issues': issues}, indent=2) + '\n')
                return None, None, None

        engine.resolve_exit_execution = collect

    installation.install_compatible_action_prices = collect_install
    try:
        replay.audit.main()
    except RuntimeError as error:
        if not str(error).startswith('No executable price or verified corporate-action settlement for:'):
            raise
        result = {'status': 'BLOCKED_NO_VALID_UNIVERSE_RETURN',
                  'basis_issues': issues, 'unresolved_executions': str(error),
                  'universe_return': None, 'ranking_value_added': None}
        target.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'status': result['status'], 'basis_issue_count': len(issues),
                          'report': str(target)}), flush=True)
    else:
        target.write_text(json.dumps({'status': 'MODEL_COMPLETED_REQUIRES_INDEPENDENT_REVIEW',
                                     'basis_issues': issues}, indent=2) + '\n')


if __name__ == '__main__':
    main()
