import unittest
from types import SimpleNamespace
from audit_dated_action_chain import identity, install_dated_action_chain
from audit_action_price_install import install_compatible_action_prices


def stock(day, successor, ratio=1, cash=0, **extra):
    return dict(effective_date=day, successor_ticker=successor,
                shares_per_share=ratio, cash_per_share=cash,
                reason='STOCK_MERGER', **extra)


class DatedActionChainTests(unittest.TestCase):
    def build(self):
        actions = {'OLD': stock('2024-03-01', 'MID', .674, reintroduced_date='2024-03-04'),
                   'MID': stock('2024-03-04', 'OLD')}
        cache = {'2024-02-29': {'OLD': {'open': 10, 'close': 10}},
                 '2024-03-01': {'MID': {'open': 20, 'close': 21}},
                 '2024-03-04': {'OLD': {'open': 220, 'close': 230}},
                 '2024-04-01': {'OLD': {'open': 240, 'close': 250}}}
        def terminal(rows, days, ticker, target, entry, latest):
            for day in days:
                if max(target, entry) <= day <= latest and ticker in rows[day]:
                    return day, rows[day][ticker], None
            return None, None, None
        engine = SimpleNamespace(STOCK_CORPORATE_ACTIONS=actions, CASH_CORPORATE_ACTIONS={},
                                 get_from_map=lambda rows, ticker: rows.get(ticker),
                                 resolve_exit_execution=terminal,
                                 position_close_on_day=lambda rows, ticker, day: (rows[day][ticker]['close'], None))
        install_dated_action_chain(engine)
        install_compatible_action_prices(engine, lambda rows, ticker, day: 10 if ticker == 'OLD' and day >= '2024-03-04' else 1)
        return engine, cache

    def test_old_holder_crosses_two_changes_without_reusing_old_basis(self):
        engine, cache = self.build()
        day, row, action = engine.resolve_exit_execution(cache, sorted(cache), 'OLD', '2024-04-01', '2024-02-29', '2024-04-01')
        self.assertEqual(day, '2024-04-01')
        self.assertAlmostEqual(row['open'], 24 * .674)
        self.assertAlmostEqual(action['shares_per_share'], .674)
        self.assertEqual(len(action['action_chain']), 2)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2024-03-04', '2024-02-29')[0], 23 * .674)

    def test_new_generation_uses_own_unconverted_price(self):
        engine, cache = self.build()
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2024-03-04', '2024-03-04')[0], 230)
        self.assertTrue(engine.has_executable_planned_entry('OLD', '2024-03-04'))
        self.assertFalse(engine.has_executable_planned_entry('OLD', '2024-03-01'))

    def test_intermediate_session_is_not_backdated_to_final_symbol(self):
        engine, cache = self.build()
        day, row, action = engine.resolve_exit_execution(cache, sorted(cache), 'OLD', '2024-03-01', '2024-02-29', '2024-04-01')
        self.assertEqual(day, '2024-03-01')
        self.assertAlmostEqual(row['open'], 20 * .674)
        self.assertEqual(action['valuation_ticker'], 'MID')

    def test_cash_components_follow_prior_share_quantity(self):
        actions = {'A': stock('2024-01-02', 'B', 2, 3),
                   'B': stock('2024-01-03', 'C', .5, 4)}
        ticker, ratio, action = identity(actions, 'A', '2024-01-04', '2024-01-01')
        self.assertEqual(ticker, 'C')
        self.assertEqual(ratio, 1)
        self.assertEqual(action['cash_per_share'], 11)

    def test_symbol_return_does_not_apply_previous_generation_to_new_holder(self):
        actions = {'A': stock('2023-06-07', 'B', reintroduced_date='2025-11-11'),
                   'B': stock('2025-11-11', 'A')}
        self.assertEqual(identity(actions, 'A', '2026-01-01', '2025-12-01'), ('A', 1, None))
        self.assertEqual(identity(actions, 'A', '2026-01-01'), ('A', 1, None))
        self.assertEqual(identity(actions, 'A', '2023-07-01', '2023-06-01')[0], 'B')

    def test_cash_retirement_does_not_block_reused_symbol(self):
        engine, _ = self.build()
        engine.CASH_CORPORATE_ACTIONS['B'] = dict(effective_date='2025-01-27',
                                                 reintroduced_date='2025-05-09')
        self.assertFalse(engine.has_executable_planned_entry('B', '2025-02-03'))
        self.assertTrue(engine.has_executable_planned_entry('B', '2025-05-09'))

    def test_later_cash_merger_uses_accumulated_original_share_units(self):
        cash = dict(effective_date='2024-01-04', cash_per_share=5,
                    reason='CASH_MERGER', execution='cash-settlement')
        cache = {'2024-01-01': {'A': {'close': 40}},
                 '2024-01-02': {'B': {'close': 20}}, '2024-01-04': {}}
        engine = SimpleNamespace(STOCK_CORPORATE_ACTIONS={'A': stock('2024-01-02', 'B', 2, 3)},
                                 CASH_CORPORATE_ACTIONS={'B': cash},
                                 get_from_map=lambda rows, ticker: rows.get(ticker),
                                 resolve_exit_execution=lambda *args: ('2024-01-04', {'open': 5, 'close': 5}, cash),
                                 position_close_on_day=lambda *args: (None, None))
        install_dated_action_chain(engine)
        install_compatible_action_prices(engine, lambda *args: 4)
        day, row, action = engine.resolve_exit_execution(cache, sorted(cache), 'A', '2024-01-04',
                                                         '2024-01-01', '2024-01-04')
        self.assertEqual(day, '2024-01-04')
        self.assertEqual(row['open'], (2 * 5 + 3) * 4)
        self.assertEqual(action['cash_per_share'], 13)


if __name__ == '__main__':
    unittest.main()
