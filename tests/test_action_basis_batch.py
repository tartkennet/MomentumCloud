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
