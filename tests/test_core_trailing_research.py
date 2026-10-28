import json
import unittest
import test_core_stop_research as support
from research_core_trailing import TrailingLedger


class TrailingResearchTests(support.StopResearchTests):
    def held(self, **kwargs):
        values = dict(cash=0, shares={'A': 10}, high_water={'A': 100},
                      previous_risk=True, selection_month='2024-01')
        if 'entry_basis' in kwargs:
            kwargs['high_water'] = kwargs.pop('entry_basis')
        values.update(kwargs)
        return TrailingLedger(**values)

    def test_addition_uses_weighted_average_entry_and_partial_sale_retains_it(self):
        s = self.held(cash=1000)
        d = support.Data({'2024-01-30': {'A': [50, 50, 10000]}})
        s.pending = support.target('2024-01-29', nav=1000, A=1)
        s.execute_open(d, '2024-01-30')
        self.assertEqual(s.shares, {'A': 20})
        self.assertEqual(s.high_water['A'], 100)
        s.pending = support.target('2024-01-29', nav=250, A=1)
        s.execute_open(d, '2024-01-30')
        self.assertEqual(s.shares, {'A': 5})
        self.assertEqual(s.high_water['A'], 100)

    def test_split_and_reverse_split_do_not_create_stop(self):
        for before, after, close in ((1, 2, 50), (10, 1, 1000)):
            s = self.held()
            d = support.Data({'2024-01-30': {'A': [close, close, 10000]}},
                     splits=[{'ticker': 'A', 'execution_date': '2024-01-30',
                              'split_from': before, 'split_to': after}])
            s.step(d, '2024-01-30')
            self.assertFalse(s.stop_pending)
            self.assertAlmostEqual(s.high_water['A'], close)
            self.assertAlmostEqual(s.shares['A'] * close, 1000)

    def test_stock_exchange_averages_existing_successor_basis(self):
        s = self.held(shares={'A': 10, 'B': 5}, entry_basis={'A': 100, 'B': 20})
        d = support.Data({'2024-01-30': {'B': [44, 44, 10000]}}, stock_actions={
            'A': {'effective_date': '2024-01-30', 'shares_per_share': 2,
                  'successor_ticker': 'B', 'reason': 'STOCK_MERGER'}})
        s.step(d, '2024-01-30')
        self.assertAlmostEqual(s.high_water['B'], 44)
        self.assertEqual(s.shares, {'B': 25})
        self.assertFalse(s.stop_pending)

    def test_checkpoint_resume_matches_continuous_ledger(self):
        d = support.Data({'2024-01-30': {'A': [100, 85, 10000]},
                          '2024-01-31': {'A': [60, 65, 10000]}})
        continuous = self.held()
        continuous.step(d, '2024-01-30')
        resumed = TrailingLedger(**json.loads(json.dumps(continuous.to_dict())))
        continuous.step(d, '2024-01-31')
        resumed.step(d, '2024-01-31')
        self.assertEqual(continuous.to_dict(), resumed.to_dict())

    def test_trailing_reference_protects_accumulated_gain(self):
        s = self.held()
        d = support.Data({'2024-01-29': {'A': [100, 150, 10000]},
                          '2024-01-30': {'A': [150, 130, 10000]},
                          '2024-01-31': {'A': [125, 126, 10000]}})
        s.step(d, '2024-01-29')
        self.assertEqual(s.high_water['A'], 150)
        self.assertFalse(s.stop_pending)
        s.step(d, '2024-01-30')
        self.assertTrue(s.stop_pending)
        s.step(d, '2024-01-31')
        self.assertEqual(s.shares, {})
        self.assertEqual(s.trades[0]['price'], 125)

    def test_new_buy_high_raises_reference_without_future_close(self):
        s = self.held(cash=1000)
        d = support.Data({'2024-01-30': {'A': [120, 500, 10000]}})
        s.pending = support.target('2024-01-29', nav=1800, A=1)
        s.execute_open(d, '2024-01-30')
        self.assertEqual(s.high_water['A'], 120)

    def test_split_after_gain_transforms_high_water(self):
        s = self.held(high_water={'A': 150})
        d = support.Data({'2024-01-30': {'A': [75, 74, 10000]}},
                         splits=[{'ticker': 'A', 'execution_date': '2024-01-30',
                                  'split_from': 1, 'split_to': 2}])
        s.step(d, '2024-01-30')
        self.assertEqual(s.high_water['A'], 75)
        self.assertFalse(s.stop_pending)


if __name__ == '__main__':
    unittest.main()
