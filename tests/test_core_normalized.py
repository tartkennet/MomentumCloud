import copy
import math
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import momentum_core as core
from audit_core_normalized import audit_targets
from research_core_normalized import MODEL, select_targets
from research_core_actions import EXTRA_CASH_ACTIONS, supplement
from momentum_core_data import atomic_json
from run_core_normalized_research import candidate_selection, save_case
from run_core_risk_research import audit
from test_momentum_core import MemoryData, long_data


class NormalizedTests(unittest.TestCase):
    def test_verified_merger_replaces_missing_quote_with_unspendable_claim(self):
        data = MemoryData(['2024-03-11', '2024-03-12'],
                          [{'SOVO': [22.9, 22.9, 1_000_000]}, {}])
        original = {}
        data.source = SimpleNamespace(cash_actions=original)
        supplement(data)
        self.assertEqual(original, {})
        self.assertNotIn('pay_date', data.cash_actions['SOVO'])
        ledger = core.Ledger(cash=0, shares={'SOVO': 10})
        ledger.events_before_open(data, '2024-03-12')
        self.assertEqual(ledger.cash, 0)
        self.assertEqual(ledger.shares, {})
        self.assertEqual(sum(r['amount'] for r in ledger.receivables), 230)
        self.assertEqual(ledger.close_value(data, '2024-03-12')[0], 230)
        self.assertFalse(any(t['side'] in ('BUY', 'SELL') for t in ledger.trades))
        self.assertEqual(ledger.fees, 0)

    def test_supplement_preserves_unpriced_right_and_rejects_conflicting_facts(self):
        data = MemoryData(['2025-06-25'], [{}])
        data.source = SimpleNamespace(cash_actions={})
        supplement(data)
        ledger = core.Ledger(cash=0, shares={'RGLS': 10})
        ledger.events_before_open(data, '2025-06-25')
        self.assertEqual(sum(r['amount'] for r in ledger.receivables), 70)
        right = next(r for r in ledger.receivables if r['reason'] == 'CONTINGENT_VALUE_RIGHT_UNPRICED')
        self.assertEqual(right['amount'], 0)
        self.assertEqual(right['maximum_amount'], 70)
        with self.assertRaises(ValueError):
            supplement(data)

    def test_ranking_scales_momentum_without_changing_eligibility(self):
        data = long_data()
        for i, day in enumerate(data.days):
            price = 30 * math.exp(i * .006 + math.sin(i) * .3)
            data.by_day[day]['S19'] = [price, price, 1_000_000]
        day = data.days[-1]
        baseline, n0 = core.select_targets(data, day)
        candidate, n1 = select_targets(data, day)
        self.assertEqual(n0, n1)
        self.assertEqual(baseline[0]['ticker'], 'S19')
        self.assertNotEqual(candidate[0]['ticker'], 'S19')
        self.assertEqual(len(candidate), 15)
        self.assertAlmostEqual(sum(r['weight'] for r in candidate), 1)
        self.assertTrue(all(0 < r['weight'] <= .1 for r in candidate))

    def test_future_data_cannot_change_past_ranking(self):
        data = long_data()
        day = data.days[-2]
        before = select_targets(data, day)
        data.by_day[data.days[-1]]['S19'] = [1, 1, 1]
        data.splits.append({'ticker': 'S19', 'execution_date': data.days[-1],
                            'split_from': 100, 'split_to': 1})
        self.assertEqual(before, select_targets(data, day))

    def test_missing_prices_and_pit_exclusions_stay_excluded(self):
        data = long_data()
        del data.by_day[data.days[-100]]['S19']
        data.records[-2]['active'] = False
        data.records[-3]['type'] = 'ETF'
        data.by_day[data.days[-1]]['S16'][1] = 9
        rows, count = select_targets(data, data.days[-1])
        self.assertEqual(count, 16)
        self.assertFalse({'S19', 'S18', 'S17', 'S16'} & {r['ticker'] for r in rows})

    def test_ties_are_deterministic_and_missing_sleeves_remain_cash(self):
        data = long_data()
        data.records = data.records[:2]
        for bars in data.by_day.values():
            bars['S01'] = list(bars['S00'])
        rows, count = select_targets(data, data.days[-1])
        self.assertEqual([r['ticker'] for r in rows], ['S00', 'S01'])
        self.assertEqual(count, 2)
        self.assertAlmostEqual(sum(r['weight'] for r in rows), 2 / 15)

    def replay_fixture(self):
        data = long_data()
        data.sessions = data.days[252:]
        config = replace(core.CONFIG, model=MODEL)
        ledger = core.Ledger()
        with patch.object(core, 'select_targets', select_targets):
            for day in data.sessions:
                ledger.step(data, day, config)
        return data, config, ledger

    def test_independent_audit_accepts_and_rejects_corrupted_ranks_weights_and_fields(self):
        data, config, ledger = self.replay_fixture()
        report = audit_targets(data, config, ledger.targets, ledger.trades)
        self.assertEqual(report['status'], 'PASS')
        self.assertGreater(report['eligible_rows_checked'], 0)
        for corruption in ('rank', 'weight', 'score', 'population', 'date'):
            with self.subTest(corruption=corruption):
                targets = copy.deepcopy(ledger.targets)
                row = next(r for r in targets if r['risk_on'])
                if corruption == 'rank':
                    row['targets'][0], row['targets'][1] = row['targets'][1], row['targets'][0]
                elif corruption == 'weight':
                    row['targets'][0]['weight'] += .001
                elif corruption == 'score':
                    row['targets'][0]['risk_normalized_score'] *= 1.01
                elif corruption == 'population':
                    row['eligible_count'] += 1
                else:
                    row['date'] = data.days[-1]
                with self.assertRaises(AssertionError):
                    audit_targets(data, config, targets, ledger.trades)

    def test_independent_audit_rejects_delayed_fill(self):
        data, config, ledger = self.replay_fixture()
        trades = copy.deepcopy(ledger.trades)
        self.assertTrue(trades)
        trades[0]['date'] = data.sessions[2]
        with self.assertRaisesRegex(AssertionError, 'next observed session'):
            audit_targets(data, config, ledger.targets, trades)

    def test_saved_checkpoint_resume_equals_uninterrupted_account(self):
        data, config, full = self.replay_fixture()
        split = len(data.sessions) // 2
        resumed = core.Ledger()
        with candidate_selection():
            for day in data.sessions[:split]:
                resumed.step(data, day, config)
            import json
            resumed = core.Ledger(**json.loads(json.dumps(resumed.to_dict())))
            for day in data.sessions[split:]:
                resumed.step(data, day, config)
        self.assertEqual(resumed.to_dict(), full.to_dict())

    def test_selector_restored_even_on_error_and_cache_cannot_be_mutated(self):
        original = core.select_targets
        data = long_data()
        day = data.days[-1]
        with self.assertRaises(RuntimeError):
            with candidate_selection():
                before = core.select_targets(data, day, core.CONFIG)
                core.select_targets(data, day, core.CONFIG)[0][0]['weight'] = 100
                self.assertEqual(core.select_targets(data, day, core.CONFIG), before)
                raise RuntimeError('interrupted')
        self.assertIs(core.select_targets, original)

    def test_independent_audit_detects_changed_signal_prices(self):
        data, config, ledger = self.replay_fixture()
        first = ledger.targets[0]['date']
        data.by_day[first]['SPY'][1] = .01
        with self.assertRaisesRegex(AssertionError, 'Signal dates/regime'):
            audit_targets(data, config, ledger.targets, ledger.trades)

    def test_exported_account_is_independently_reconciled_end_to_end(self):
        data = long_data()
        data.sessions = data.days[252:]
        data.input_fingerprint = lambda: 'synthetic-test-only'
        config = replace(core.CONFIG, model=MODEL)
        strategy, benchmark = core.Ledger(first_is_month_boundary=True), core.Ledger()
        with candidate_selection():
            for day in data.sessions:
                benchmark.step(data, day, config, benchmark=True)
                strategy.step(data, day, config)
        metrics, periods = core.metrics(strategy, benchmark)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, cache = root / 'case', root / 'cache'
            end = data.sessions[-1]
            atomic_json(cache / f'splits-2022-06-30-{end}-v1.json.gz', [])
            atomic_json(cache / f'dividends-2024-01-01-{end}-v1.json.gz', [])
            for day in data.sessions:
                atomic_json(cache / 'raw-v1' / f'{day}.json.gz', {'bars': data.bars(day)})
            decision = save_case(folder, data, config, strategy, benchmark, metrics, periods, {}, 'test-only')
            report = audit(cache, folder)
            self.assertEqual(report['status'], 'PASS')
            self.assertLess(report['max_nav_error_usd'], 1e-6)
            self.assertFalse(decision['live_approved'])
            self.assertFalse(decision['broker_orders_enabled'])
            self.assertEqual(decision['model'], MODEL)
            state = json.loads((folder / 'checkpoint.json').read_text())
            self.assertEqual(state['strategy'], strategy.to_dict())


if __name__ == '__main__':
    unittest.main()
