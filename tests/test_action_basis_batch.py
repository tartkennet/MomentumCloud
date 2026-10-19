import unittest
from datetime import datetime, timezone

from audit_action_basis_batch import inspect_pair


class ActionBasisBatchTests(unittest.TestCase):
    request = {'ticker': 'TEST', 'day': '2023-05-01', 'purpose': 'original-basis'}

    def test_missing_pair_collects_both_requests_without_inference(self):
        calls = []
        def missing(_client, path, params):
            calls.append(params['adjusted'])
            raise RuntimeError('OFFLINE_REQUEST_MISSING ' + path)
        result = inspect_pair(self.request, missing)
        self.assertEqual(calls, ['true', 'false'])
        self.assertEqual(len(result['missing_requests']), 2)
        self.assertEqual(result['observations'], {})

    def test_later_quote_is_not_backdated(self):
        timestamp = datetime(2023, 5, 3, tzinfo=timezone.utc).timestamp() * 1000
        # Synthetic unit-test values, not historical market prices.
        def later(*_args):
            return {'results': [dict(o=1, h=1, l=1, c=1, v=1, t=timestamp)]}
        result = inspect_pair(self.request, later)
        self.assertEqual(result['observations'], {})
        self.assertEqual(len(result['missing_requests']), 2)
        self.assertEqual({r['reason'] for r in result['missing_requests']},
                         {'OBSERVATION_DATE_DOES_NOT_MATCH_REQUEST'})

    def test_unexpected_provider_error_is_not_hidden_as_missing_data(self):
        def broken(*_args):
            raise RuntimeError('BROKEN_FILE_HASH')
        with self.assertRaisesRegex(RuntimeError, 'BROKEN_FILE_HASH'):
            inspect_pair(self.request, broken)

    def test_zero_volume_reference_mark_is_not_a_verified_trade_pair(self):
        timestamp = datetime(2023, 5, 1, tzinfo=timezone.utc).timestamp() * 1000
        def no_trades(*_args):
            return {'results': [dict(o=10, h=10, l=10, c=10, v=0, t=timestamp)]}
        result = inspect_pair(self.request, no_trades)
        self.assertEqual(result['observations'], {})
        self.assertEqual(len(result['missing_requests']), 2)
        self.assertEqual({item['reason'] for item in result['missing_requests']},
                         {'NO_POSITIVE_OBSERVED_TRADE_VOLUME'})

    def test_actual_positive_volume_observations_are_preserved(self):
        timestamp = datetime(2023, 5, 1, tzinfo=timezone.utc).timestamp() * 1000
        def observed(_client, _path, params):
            value = 5 if params['adjusted'] == 'true' else 10
            return {'results': [dict(o=value, h=value, l=value, c=value, v=2, t=timestamp)]}
        result = inspect_pair(self.request, observed)
        self.assertEqual(result['status'], 'OBSERVED_PAIR_ONLY')
        self.assertEqual(result['observations']['raw'][0]['o'], 10)
        self.assertEqual(result['observations']['adjusted'][0]['o'], 5)
        self.assertEqual(result['missing_requests'], [])
