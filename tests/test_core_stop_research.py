import copy
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from momentum_core import CONFIG, DataBlocked, Ledger
from research_core_stop import StopLedger


class Data:
    def __init__(self, bars, splits=(), cash_actions=None, stock_actions=None):
        self.by_day = bars
        self.splits, self.dividends = list(splits), []
        self.cash_actions, self.stock_actions = cash_actions or {}, stock_actions or {}

    def bars(self, day):
        return self.by_day[day]


def target(day, nav=1000, **weights):
    return {'signal_date': day, 'signal_nav': nav,
            'targets': [{'ticker': t, 'weight': w} for t, w in weights.items()]}


class StopResearchTests(unittest.TestCase):
    def setUp(self):
        self.risk = patch('momentum_core.risk_on', return_value=True)
        self.select = patch('momentum_core.select_targets',
                            return_value=([{'ticker': 'A', 'weight': 1.0}], 1))
        self.risk.start()
        self.select.start()
        self.addCleanup(self.risk.stop)
        self.addCleanup(self.select.stop)

    def held(self, **kwargs):
        values = dict(cash=0, shares={'A': 10}, entry_basis={'A': 100},
                      previous_risk=True, selection_month='2024-01')
        values.update(kwargs)
        return StopLedger(**values)

    def test_signal_close_is_not_fill_and_gap_can_exceed_ten_percent(self):
        d = Data({'2024-01-30': {'A': [100, 85, 10000]},
                  '2024-01-31': {'A': [60, 65, 10000]}})
        s = self.held()
        s.step(d, '2024-01-30')
        self.assertEqual(s.shares, {'A': 10})
        self.assertEqual(s.cash, 0)
        s.step(d, '2024-01-31')
        self.assertEqual(s.shares, {})
        self.assertAlmostEqual(s.cash, 599.1)
        self.assertEqual(s.trades[0]['price'], 60)
        self.assertEqual(s.trades[0]['signal_date'], '2024-01-30')

    def test_exact_threshold_triggers_and_above_does_not(self):
        for close, triggered in ((90.0, True), (90.001, False)):
            s = self.held()
            s.step(Data({'2024-01-30': {'A': [100, close, 10000]}}), '2024-01-30')
            self.assertEqual(bool(s.stop_pending), triggered)

    def test_stop_exit_does_not_rebalance_other_positions(self):
        d = Data({'2024-01-30': {'A': [100, 80, 10000], 'B': [40, 42, 10000]},
                  '2024-01-31': {'A': [75, 75, 10000], 'B': [45, 46, 10000]}})
        s = self.held(shares={'A': 10, 'B': 7}, entry_basis={'A': 100, 'B': 40})
        s.step(d, '2024-01-30')
        s.step(d, '2024-01-31')
        self.assertEqual(s.shares, {'B': 7})
        self.assertEqual([r['ticker'] for r in s.trades], ['A'])

    def test_missing_stop_open_blocks(self):
        s = self.held(stop_pending={'A': {'signal_date': '2024-01-30'}})
        with self.assertRaises(DataBlocked):
            s.step(Data({'2024-01-31': {'A': [None, 80, 10000]}}), '2024-01-31')

    def test_split_and_reverse_split_do_not_create_stop(self):
        for before, after, close in ((1, 2, 50), (10, 1, 1000)):
            s = self.held()
            d = Data({'2024-01-30': {'A': [close, close, 10000]}},
                     splits=[{'ticker': 'A', 'execution_date': '2024-01-30',
                              'split_from': before, 'split_to': after}])
            s.step(d, '2024-01-30')
            self.assertFalse(s.stop_pending)
            self.assertAlmostEqual(s.entry_basis['A'], close)
            self.assertAlmostEqual(s.shares['A'] * close, 1000)

    def test_ticker_change_remaps_pending_exit_and_basis(self):
        s = self.held(stop_pending={'A': {'signal_date': '2024-01-29'}},
                      stopped_month={'A': '2024-01'})
        d = Data({'2024-01-30': {'B': [70, 72, 10000]}}, stock_actions={
            'A': {'effective_date': '2024-01-30', 'shares_per_share': 1,
                  'successor_ticker': 'B', 'reason': 'TICKER_CHANGE'}})
        s.step(d, '2024-01-30')
        self.assertEqual(s.shares, {})
        self.assertEqual(s.trades[0]['ticker'], 'B')
        self.assertAlmostEqual(s.cash, 698.95)

    def test_stock_exchange_averages_existing_successor_basis(self):
        s = self.held(shares={'A': 10, 'B': 5}, entry_basis={'A': 100, 'B': 20})
        d = Data({'2024-01-30': {'B': [44, 44, 10000]}}, stock_actions={
            'A': {'effective_date': '2024-01-30', 'shares_per_share': 2,
                  'successor_ticker': 'B', 'reason': 'STOCK_MERGER'}})
        s.step(d, '2024-01-30')
        self.assertAlmostEqual(s.entry_basis['B'], 44)
        self.assertEqual(s.shares, {'B': 25})
        self.assertFalse(s.stop_pending)

    def test_cash_merger_cancels_stop_without_fake_stock_fill(self):
        s = self.held(stop_pending={'A': {'signal_date': '2024-01-29'}})
        d = Data({'2024-01-30': {}}, cash_actions={
            'A': {'effective_date': '2024-01-30', 'cash_per_share': 75}})
        s.step(d, '2024-01-30')
        self.assertEqual(s.shares, {})
        self.assertEqual(s.cash, 0)
        self.assertEqual(s.receivables[0]['amount'], 750)
        self.assertEqual([r['side'] for r in s.trades], ['CASH_MERGER_CLAIM'])

    def test_addition_uses_weighted_average_entry_and_partial_sale_retains_it(self):
        s = self.held(cash=1000)
        d = Data({'2024-01-30': {'A': [50, 50, 10000]}})
        s.pending = target('2024-01-29', nav=1000, A=1)
        s.execute_open(d, '2024-01-30')
        self.assertEqual(s.shares, {'A': 20})
        self.assertAlmostEqual(s.entry_basis['A'], 75)
        s.pending = target('2024-01-29', nav=250, A=1)
        s.execute_open(d, '2024-01-30')
        self.assertEqual(s.shares, {'A': 5})
        self.assertAlmostEqual(s.entry_basis['A'], 75)

    def test_fraction_is_not_sold_at_invented_cash_in_lieu(self):
        s = self.held(shares={'A': 1.5})
        d = Data({'2024-01-30': {'A': [80, 80, 10000]},
                  '2024-01-31': {'A': [70, 70, 10000]}})
        s.step(d, '2024-01-30')
        s.step(d, '2024-01-31')
        self.assertEqual(s.shares, {'A': .5})
        self.assertEqual(s.trades[0]['quantity'], 1)
        self.assertFalse(s.stop_pending)

    def test_stop_precedes_monthly_target_and_waits_until_new_month(self):
        s = self.held(selection_month='2023-12')
        d = Data({'2024-01-30': {'A': [100, 80, 10000]},
                  '2024-01-31': {'A': [75, 75, 10000]},
                  '2024-02-01': {'A': [75, 75, 10000]}})
        s.step(d, '2024-01-30')
        self.assertEqual(s.pending['targets'], [])
        s.step(d, '2024-01-31')
        self.assertNotIn('A', s.shares)
        s.step(d, '2024-02-01')
        self.assertEqual(s.pending['targets'], [{'ticker': 'A', 'weight': 1.0}])

    def test_regime_recovery_does_not_rebuy_stopped_name_same_month(self):
        s = self.held(cash=1000, shares={}, entry_basis={}, previous_risk=False,
                      stopped_month={'A': '2024-01'})
        s.step(Data({'2024-01-30': {'A': [100, 100, 10000]}}), '2024-01-30')
        self.assertEqual(s.pending['targets'], [])

    def test_checkpoint_resume_matches_continuous_ledger(self):
        d = Data({'2024-01-30': {'A': [100, 85, 10000]},
                  '2024-01-31': {'A': [60, 65, 10000]}})
        continuous = self.held()
        continuous.step(d, '2024-01-30')
        resumed = StopLedger(**json.loads(json.dumps(continuous.to_dict())))
        continuous.step(d, '2024-01-31')
        resumed.step(d, '2024-01-31')
        self.assertEqual(continuous.to_dict(), resumed.to_dict())

    def test_future_gap_cannot_change_prior_stop_signal(self):
        s = self.held()
        d = Data({'2024-01-30': {'A': [100, 95, 10000]},
                  '2024-01-31': {'A': [1, 1, 10000]}})
        s.step(d, '2024-01-30')
        first = copy.deepcopy(s.to_dict())
        d.by_day['2024-01-31']['A'] = [1000, 1000, 1]
        other = self.held()
        other.step(d, '2024-01-30')
        self.assertEqual(first, other.to_dict())

    def test_unmodified_benchmark_class_is_required(self):
        with self.assertRaises(ValueError):
            self.held().step(Data({}), '2024-01-30', benchmark=True)


if __name__ == '__main__':
    unittest.main()
