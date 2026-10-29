import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import momentum_core as core
from momentum_core_data import atomic_json
from research_core_ledger import ResearchLedger, STOCK_COMPLETIONS, DISTRIBUTIONS
from run_core_normalized_research import save_case, accounting_audit, payment_policy
from test_momentum_core import MemoryData, order


class EventCompletions(unittest.TestCase):
    def test_cancelled_missing_buy_keeps_its_original_signal_date(self):
        d = MemoryData(['2024-01-02', '2024-01-03'], [{}, {}])
        l = ResearchLedger(pending=order(d.days[0], 100000, MISSING=.1))
        l.execute_open(d, d.days[1])
        self.assertEqual(l.trades[0]['signal_date'], d.days[0])
        self.assertEqual(l.trades[0]['date'], d.days[1])
        self.assertEqual(l.trades[0]['side'], 'BUY_CANCELLED_NO_OPEN')
        self.assertEqual(l.cash, 100000)

    def test_payment_policies_preserve_cross_boundary_and_unobserved_future_claims(self):
        d = SimpleNamespace(days=['2026-10-22', '2026-10-23', '2026-10-26'],
                            sessions=['2026-10-22', '2026-10-23'],
                            payment_sessions=['2026-10-22', '2026-10-23', '2026-10-26'])
        d.source = SimpleNamespace(cash_actions={'A': {'effective_date': '2026-10-23', 'cash_per_share': 10},
                                   'FUTURE': {'effective_date': '2026-12-01', 'cash_per_share': 20}}, stock_actions={})
        payment_policy(d, 1)
        self.assertEqual(d.cash_actions['A']['pay_date'], '2026-10-26')
        assumptions = payment_policy(d, 20)
        self.assertNotIn('pay_date', d.cash_actions['A'])
        self.assertEqual(len(assumptions), 1)
        self.assertTrue(assumptions[0]['payment_after_observed_window'])
        payment_policy(d, None)
        self.assertNotIn('pay_date', d.cash_actions['A'])

    def test_ael_preserves_cash_stock_and_fractional_rights(self):
        d = MemoryData(['2024-05-03'], [{'BAM': [40, 41, 1_000_000]}],
                       stock_actions={'AEL': dict(STOCK_COMPLETIONS['AEL'])})
        l = ResearchLedger(cash=0, shares={'AEL': 101, 'BAM': 2})
        l.events_before_open(d, d.days[0])
        self.assertAlmostEqual(l.shares['BAM'], 2 + 101 * .45464)
        self.assertAlmostEqual(l.receivables[0]['amount'], 101 * 38.85)
        self.assertEqual(l.cash, 0)
        l.pending = order('2024-05-02', 10000)
        l.execute_open(d, d.days[0])
        self.assertAlmostEqual(l.shares['BAM'], (2 + 101 * .45464) % 1)
        self.assertEqual([t['side'] for t in l.trades], ['STOCK_MERGER_CASH_CLAIM', 'SELL'])

    def test_rna_rename_distribution_cash_and_reused_symbol_stay_separate(self):
        days = ['2026-02-26', '2026-02-27']
        d = MemoryData(days, [{'RNAM': [73, 73, 1_000_000]}, {'RNA': [10, 11, 1_000_000]}],
                       stock_actions={'RNA': dict(STOCK_COMPLETIONS['RNA'])},
                       cash_actions={'RNAM': {'effective_date': days[1], 'cash_per_share': 72}})
        d.distributions = DISTRIBUTIONS
        l = ResearchLedger(cash=0, shares={'RNA': 101})
        l.events_before_open(d, days[0])
        self.assertEqual(l.shares, {'RNAM': 101})
        l.events_before_open(d, days[1])
        self.assertEqual(l.shares, {'RNA': 10.100000000000001})
        self.assertEqual(sum(r['amount'] for r in l.receivables), 7272)
        self.assertAlmostEqual(l.close_value(d, days[1])[0], 7272 + 10.1 * 11)
        self.assertEqual(l.cash, 0)

    def test_suspension_mark_is_not_spendable_and_cannot_fill_an_order(self):
        d = MemoryData(['2025-06-16', '2025-06-17'], [{}, {}],
                       cash_actions={'PLYA': {'effective_date': '2025-06-17', 'cash_per_share': 13.5}})
        d.halt_marks = {'2025-06-16': {'ticker': 'PLYA', 'value': 13.49}}
        l = ResearchLedger(cash=0, shares={'PLYA': 100})
        self.assertEqual(l.close_value(d, d.days[0]), (1349., 1349., 0))
        l.pending = order('2025-06-13', 1349)
        with self.assertRaises(core.DataBlocked):
            l.execute_open(d, d.days[0])
        l.pending = None
        l.events_before_open(d, d.days[1])
        self.assertEqual(l.shares, {})
        self.assertEqual(l.cash, 0)
        self.assertEqual(l.close_value(d, d.days[1]), (1350., 0, 1350.))

    def test_mixed_and_spin_accounts_are_independently_reconciled_and_corruption_rejected(self):
        # A complete synthetic multi-month book exercises the auditor's event
        # reconstruction, not a production selector or copied expected NAV.
        days = ['2026-02-24', '2026-02-25', '2026-02-26', '2026-02-27', '2026-03-02']
        bars = [{'SPY': [100, 100, 1e6], 'RNA': [70, 71, 1e6], 'AEL': [55, 56, 1e6]},
                {'SPY': [100, 101, 1e6], 'RNA': [71, 72, 1e6], 'AEL': [56, 57, 1e6]},
                {'SPY': [101, 102, 1e6], 'RNAM': [72, 73, 1e6], 'BAM': [40, 41, 1e6]},
                {'SPY': [102, 103, 1e6], 'RNA': [10, 11, 1e6], 'BAM': [41, 42, 1e6]},
                {'SPY': [103, 104, 1e6], 'RNA': [11, 12, 1e6], 'BAM': [42, 43, 1e6]}]
        ael = dict(STOCK_COMPLETIONS['AEL'], effective_date=days[2])
        d = MemoryData(days, bars, stock_actions={'AEL': ael, 'RNA': STOCK_COMPLETIONS['RNA']},
                       cash_actions={'RNAM': {'effective_date': days[3], 'cash_per_share': 72}})
        d.distributions = DISTRIBUTIONS
        d.input_fingerprint = lambda: 'synthetic-event-test'
        s, b = ResearchLedger(first_is_month_boundary=True), core.Ledger()
        # Place one close-formed order. Disable later selections so received
        # fractional shares and unpaid cash survive through the audit horizon.
        with patch.object(core, 'risk_on', return_value=True), patch.object(core, 'select_targets',
                return_value=([{'ticker': 'RNA', 'weight': .1}, {'ticker': 'AEL', 'weight': .1}], 2)):
            for day in days:
                b.step(d, day, benchmark=True)
                s.step(d, day)
                if day == days[0]:
                    s.selection_month = '2026-03'
        m, periods = core.metrics(s, b)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache, folder = root / 'cache', root / 'results'
            atomic_json(cache / f'splits-2022-06-30-{days[-1]}-v1.json.gz', [])
            atomic_json(cache / f'dividends-2024-01-01-{days[-1]}-v1.json.gz', [])
            for day in days:
                atomic_json(cache / 'raw-v1' / f'{day}.json.gz', {'bars': d.bars(day)})
            save_case(folder, d, core.CONFIG, s, b, m, periods, {}, 'test')
            self.assertEqual(accounting_audit(cache, folder)['status'], 'PASS')
            facts = json.loads((folder / 'experiment_facts.json').read_text())
            facts['stock_actions']['AEL']['cash_per_share'] += 1
            atomic_json(folder / 'experiment_facts.json', facts)
            with self.assertRaises(AssertionError):
                accounting_audit(cache, folder)
