"""Publication must not silently turn rejected history into forward returns."""
import hashlib
import json
from pathlib import Path
import unittest


class PublicationTests(unittest.TestCase):
    def test_completed_evidence_retains_failures_and_safety_status(self):
        r = json.loads(Path('public/data/stocks10-research.json').read_text())
        self.assertTrue(r['completed'])
        self.assertEqual(r['status'], 'NO_GO')
        self.assertEqual(len(r['cases']), 40)
        self.assertTrue(all(a['decision'] == 'NO_GO' and a['audit']['status'] == 'PASS' for a in r['cases']))
        self.assertFalse(r['forward_paper_started'])
        self.assertFalse(r['live_approved'])
        self.assertFalse(r['broker_orders_enabled'])
        self.assertEqual(r['publication_nav_crosscheck'], 'PASS')
        for file, digest in r['source_files'].items():
            self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(), digest)

    def test_whole_lots_and_extra_corporate_right_are_not_hidden(self):
        r = json.loads(Path('public/data/stocks10-research.json').read_text())
        self.assertEqual(r['final_whole_stock_positions'], 10)
        self.assertEqual(r['final_fractional_corporate_entitlements'], 1)
        self.assertEqual(len(r['positions']), 11)
        self.assertNotIn('SPY', {p['ticker'] for p in r['positions']})
        right = next(p for p in r['positions'] if p['corporate_fraction_only'])
        self.assertEqual(right['ticker'], 'CDE')
        self.assertLess(right['quantity'], 1)

    def test_original_financial_limits_remain_visible(self):
        r = json.loads(Path('public/data/stocks10-research.json').read_text())
        checks = {g['gate']: g for g in r['primary']['gates']}
        self.assertEqual(checks['drawdown']['requirement'], '>= -20%')
        self.assertFalse(checks['drawdown']['pass'])
        self.assertFalse(checks['beats_spy']['pass'])
        self.assertEqual(checks['at_least_30_periods']['value'], 33)
