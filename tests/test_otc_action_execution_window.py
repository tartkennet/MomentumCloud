import unittest

import backtest_momentum_v3 as engine
from verified_exit_data import install_verified_exit_data


class OtcExecutionWindowTests(unittest.TestCase):
    def setUp(self):
        install_verified_exit_data(engine)

    def test_svb_uses_successor_quote_on_required_exit_day(self):
        cache = {'2023-03-09': {'SIVB': {'close': 106.04}},
                 '2023-03-28': {'SIVBQ': {'open': .53, 'close': .4}},
                 '2023-04-03': {'SIVBQ': {'open': .877, 'close': .98505}}}
        day, row, action = engine.resolve_exit_execution(
            cache, sorted(cache), 'SIVB', '2023-04-03', '2023-03-01', '2023-04-03')
        self.assertEqual(day, '2023-04-03')
        self.assertEqual(row['open'], .877)
        self.assertEqual(action['shares_per_share'], 1)
        self.assertEqual(action['valuation_ticker'], 'SIVBQ')

    def test_frc_may_three_price_is_not_backdated_to_may_one(self):
        cache = {'2023-04-28': {'FRC': {'open': 6.59, 'close': 3.51}},
                 '2023-05-01': {},
                 '2023-05-03': {'FRCB': {'open': .396, 'close': .3336}}}
        self.assertEqual(engine.resolve_exit_execution(
            cache, sorted(cache), 'FRC', '2023-05-01', '2023-04-03', '2023-05-01'),
            (None, None, None))

    def test_frc_only_uses_observed_quote_inside_explicit_window(self):
        cache = {'2023-04-28': {'FRC': {'close': 3.51}},
                 '2023-05-01': {},
                 '2023-05-03': {'FRCB': {'open': .396, 'close': .3336}}}
        day, row, action = engine.resolve_exit_execution(
            cache, sorted(cache), 'FRC', '2023-05-01', '2023-04-03', '2023-05-03')
        self.assertEqual(day, '2023-05-03')
        self.assertEqual(row['open'], .396)
        self.assertEqual(action['shares_per_share'], 1)
