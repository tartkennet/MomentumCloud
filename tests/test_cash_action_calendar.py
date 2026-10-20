import unittest
from types import SimpleNamespace
from audit_action_price_install import install_compatible_action_prices


class CashActionCalendarTests(unittest.TestCase):
    def build(self):
        action = dict(effective_date='2024-02-19', reason='CASH_MERGER',
                      cash_per_share=15)
        cache = {'2024-02-16': {'ICVX': {'close': 28}}, '2024-02-20': {}}
        engine = SimpleNamespace(
            get_from_map=lambda rows, ticker: rows.get(ticker),
            resolve_exit_execution=lambda *args: (
                '2024-02-19', dict(open=15, close=15, high=15, low=15), action),
            valuation_identity=lambda ticker, day: (ticker, 1, None),
            position_close_on_day=lambda *args: (None, None))
        install_compatible_action_prices(engine, lambda *args: 2)
        return engine, cache

    def test_holiday_closing_uses_next_session_in_window(self):
        engine, cache = self.build()
        day, row, action = engine.resolve_exit_execution(
            cache, sorted(cache), 'ICVX', '2024-02-20', '2024-02-16', '2024-02-20')
        self.assertEqual(day, '2024-02-20')
        self.assertEqual(action['effective_date'], '2024-02-19')
        self.assertEqual(row['open'], 30)

    def test_missing_session_fails_closed(self):
        engine, cache = self.build()
        self.assertEqual(engine.resolve_exit_execution(
            cache, ['2024-02-16'], 'ICVX', '2024-02-16',
            '2024-02-16', '2024-02-16'), (None, None, None))
