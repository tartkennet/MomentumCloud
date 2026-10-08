import unittest
from types import SimpleNamespace
from audit_action_price_install import install_compatible_action_prices


class InstalledPriceTests(unittest.TestCase):
    def build(self, cash=0, factor=10):
        action = dict(effective_date='2025-10-03', shares_per_share=1,
                      cash_per_share=cash, valuation_ticker='NEW')
        cache = {'2025-10-01': {'OLD': {'close': 28.74}},
                 '2025-10-03': {'NEW': {'close': 237.9}},
                 '2025-11-03': {'NEW': {'open': 114.1, 'close': 115}}}
        engine = SimpleNamespace(
            get_from_map=lambda rows, ticker: rows.get(ticker),
            resolve_exit_execution=lambda *args: ('2025-11-03', cache['2025-11-03']['NEW'], action),
            valuation_identity=lambda ticker, day: ('NEW', 1, action) if day >= '2025-10-03' else (ticker, 1, None),
            position_close_on_day=lambda rows, ticker, day: (rows[day][ticker]['close'], None))
        def paired(rows, ticker, day):
            if factor is None and ticker == 'NEW':
                raise RuntimeError('Missing verified basis')
            return factor if ticker == 'NEW' else 1
        install_compatible_action_prices(engine, paired)
        return engine, cache

    def test_exit_and_daily_use_same_units(self):
        engine, cache = self.build()
        _, row, action = engine.resolve_exit_execution(cache, sorted(cache), 'OLD', '2025-11-03', '2025-10-01', '2025-11-03')
        self.assertAlmostEqual(row['open'], 11.41)
        self.assertEqual(action['shares_per_share'], 1)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-10-03')[0], 23.79)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-11-03')[0], 11.5)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-10-01')[0], 28.74)

    def test_cash_component(self):
        engine, cache = self.build(cash=9)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-11-03')[0], 20.5)

    def test_missing_basis_stops_both_paths(self):
        engine, cache = self.build(factor=None)
        with self.assertRaises(RuntimeError):
            engine.position_close_on_day(cache, 'OLD', '2025-11-03')
        with self.assertRaises(RuntimeError):
            engine.resolve_exit_execution(cache, sorted(cache), 'OLD', '2025-11-03', '2025-10-01', '2025-11-03')

    def test_equal_basis_does_not_rescale(self):
        engine, cache = self.build(factor=1)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-11-03')[0], 115)

