"""Use installed legal terms to distinguish Barrick and Gold.com holdings."""
import unittest
from types import SimpleNamespace

import backtest_momentum_v3 as engine
import verified_exit_data
from audit_dated_action_chain import identity, install_dated_action_chain


class GoldSymbolGenerationTests(unittest.TestCase):
    def setUp(self):
        verified_exit_data.install_verified_exit_data(engine)
        self.actions = engine.STOCK_CORPORATE_ACTIONS

    def test_new_gold_common_stock_can_enter_after_reintroduction(self):
        isolated = SimpleNamespace(
            STOCK_CORPORATE_ACTIONS=self.actions,
            CASH_CORPORATE_ACTIONS=engine.CASH_CORPORATE_ACTIONS,
            resolve_exit_execution=lambda *args: (None, None, None),
        )
        install_dated_action_chain(isolated)
        self.assertFalse(isolated.has_executable_planned_entry('GOLD', '2025-05-09'))
        self.assertFalse(isolated.has_executable_planned_entry('GOLD', '2025-12-01'))
        self.assertTrue(isolated.has_executable_planned_entry('GOLD', '2025-12-02'))
        self.assertTrue(isolated.has_executable_planned_entry('GOLD', '2026-01-02'))

    def test_daily_identity_distinguishes_new_and_old_holders(self):
        self.assertEqual(identity(self.actions, 'GOLD', '2026-01-02'), ('GOLD', 1.0, None))
        self.assertEqual(identity(self.actions, 'GOLD', '2026-01-02', '2025-12-02'),
                         ('GOLD', 1.0, None))
        ticker, ratio, action = identity(self.actions, 'GOLD', '2026-01-02', '2025-05-01')
        self.assertEqual(ticker, 'B')
        self.assertEqual(ratio, 1.0)
        self.assertEqual(action['effective_date'], '2025-05-09')

    def test_amrk_holder_receives_gold_com_without_barrick_conversion(self):
        ticker, ratio, action = identity(self.actions, 'AMRK', '2026-01-02', '2025-12-01')
        self.assertEqual(ticker, 'GOLD')
        self.assertEqual(ratio, 1.0)
        self.assertEqual(len(action['action_chain']), 1)
        self.assertEqual(action['effective_date'], '2025-12-02')


if __name__ == '__main__':
    unittest.main()
