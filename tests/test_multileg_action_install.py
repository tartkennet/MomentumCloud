import unittest
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from audit_dated_action_chain import install_dated_action_chain
from audit_multileg_action_install import install_compatible_multileg_actions


def bar(day, opening, close):
    return {'t': datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000,
            'o': opening, 'c': close}


class MultiLegActionTests(unittest.TestCase):
    def build(self, missing=False):
        cache = {'2023-10-16': {'NCR': {'open': 30, 'close': 30}},
                 '2023-10-17': {}, '2023-11-01': {}, '2023-11-02': {}}
        observed = {}
        for ticker, raw_open, raw_close, factor in [('VYX', 10, 11, 2), ('NATL', 20, 22, 3)]:
            observed[ticker] = {}
            for basis, multiple in [('false', 1), ('true', factor)]:
                days = ['2023-10-17', '2023-11-01', '2023-11-02']
                if missing and ticker == 'NATL':
                    days.remove('2023-11-01')
                observed[ticker][basis] = {'results': [bar(d, raw_open * multiple, raw_close * multiple) for d in days]}
        def resolver(rows, days, ticker, target, entry, latest):
            row = rows.get(target, {}).get(ticker)
            return (target, row, None) if row else (None, None, None)
        engine = SimpleNamespace(STOCK_CORPORATE_ACTIONS={}, CASH_CORPORATE_ACTIONS={},
            get_from_map=lambda rows, ticker: rows.get(ticker),
            resolve_exit_execution=resolver,
            position_close_on_day=lambda rows, ticker, day, entry=None: (rows.get(day, {}).get(ticker, {}).get('close'), None))
        install_dated_action_chain(engine)
        install_compatible_multileg_actions(engine, lambda *args: 4, observed)
        return engine, cache

    def test_exit_values_both_legs_in_original_units(self):
        engine, cache = self.build()
        day, row, action = engine.resolve_exit_execution(cache, sorted(cache), 'NCR', '2023-11-01', '2023-10-02', '2023-11-01')
        self.assertEqual(day, '2023-11-01')
        self.assertEqual(row['open'], 80)
        self.assertEqual(row['close'], 88)
        self.assertEqual(len(action['valuation_legs']), 2)
        self.assertEqual(action['valuation_legs'][1]['shares_per_share'], .5)

    def test_daily_close_uses_same_compatible_two_asset_basis(self):
        engine, cache = self.build()
        value, action = engine.position_close_on_day(cache, 'NCR', '2023-11-01', '2023-10-02')
        self.assertEqual(value, 88)
        self.assertEqual(action['basis_validation'], 'PAIRED_RAW_ADJUSTED_EACH_LEG')

    def test_missing_leg_is_not_partial_or_next_day_execution(self):
        engine, cache = self.build(missing=True)
        self.assertEqual(engine.resolve_exit_execution(cache, sorted(cache), 'NCR', '2023-11-01', '2023-10-02', '2023-11-02'), (None, None, None))
        self.assertIsNone(engine.position_close_on_day(cache, 'NCR', '2023-11-01', '2023-10-02')[0])

    def test_new_stock_components_are_not_backdated_before_distribution(self):
        engine, cache = self.build()
        self.assertEqual(engine.position_close_on_day(cache, 'NCR', '2023-10-16', '2023-10-02'), (30, None))
        self.assertEqual(engine.resolve_exit_execution(cache, sorted(cache), 'NCR', '2023-10-16', '2023-10-02', '2023-10-16')[1]['open'], 30)

    def test_old_ticker_cannot_enter_after_retirement(self):
        engine, _ = self.build()
        self.assertTrue(engine.has_executable_planned_entry('NCR', '2023-10-16'))
        self.assertFalse(engine.has_executable_planned_entry('NCR', '2023-10-17'))

    def test_original_basis_is_required(self):
        engine, cache = self.build()
        cache['2023-10-16'] = {}
        with self.assertRaisesRegex(RuntimeError, 'No original pre-action basis'):
            engine.resolve_exit_execution(cache, sorted(cache), 'NCR', '2023-11-01', '2023-10-02', '2023-11-01')

    def test_execution_and_daily_valuation_do_not_change_formation_cache(self):
        engine, cache = self.build()
        before = deepcopy(cache)
        engine.resolve_exit_execution(cache, sorted(cache), 'NCR', '2023-11-01', '2023-10-02', '2023-11-01')
        engine.position_close_on_day(cache, 'NCR', '2023-11-01', '2023-10-02')
        self.assertEqual(cache, before)

    def test_unrelated_asset_keeps_its_original_execution_and_close(self):
        engine, cache = self.build()
        cache['2023-11-01']['OTHER'] = {'open': 17.25, 'close': 18.5}
        day, row, action = engine.resolve_exit_execution(cache, sorted(cache), 'OTHER', '2023-11-01', '2023-10-02', '2023-11-01')
        self.assertEqual((day, row, action), ('2023-11-01', {'open': 17.25, 'close': 18.5}, None))
        self.assertEqual(engine.position_close_on_day(cache, 'OTHER', '2023-11-01', '2023-10-02'), (18.5, None))


if __name__ == '__main__':
    unittest.main()
