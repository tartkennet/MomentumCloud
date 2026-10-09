import unittest

import backtest_momentum_v3 as engine
from audit_action_price_install import install_compatible_action_prices
from verified_exit_data import install_verified_exit_data


class CashHolidayEngineIntegrationTests(unittest.TestCase):
    def test_verified_icvx_closing_flows_through_actual_engine(self):
        install_verified_exit_data(engine)
        original_exit = engine.resolve_exit_execution
        original_close = engine.position_close_on_day
        try:
            install_compatible_action_prices(engine, lambda *args: 2)
            cache = {'2024-02-16': {'ICVX': dict(open=28, close=28, high=28, low=28)},
                     '2024-02-20': {}}
            day, row, action = engine.resolve_exit_execution(
                cache, sorted(cache), 'ICVX', '2024-02-20',
                '2024-02-16', '2024-02-20')
            self.assertEqual(day, '2024-02-20')
            self.assertEqual(action['effective_date'], '2024-02-19')
            self.assertAlmostEqual(row['open'], 30)
            self.assertEqual(action['basis_validation'], 'PAIRED_RAW_ADJUSTED')
        finally:
            engine.resolve_exit_execution = original_exit
            engine.position_close_on_day = original_close
