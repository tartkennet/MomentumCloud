"""Regression tests for dated issuer reuse, legal ratios and cash retirements."""
import unittest
import backtest_momentum_v3 as engine
import verified_exit_data
from audit_action_price_install import install_compatible_action_prices

class VerifiedActionBatchTests(unittest.TestCase):
    def setUp(self):
        verified_exit_data.install_verified_exit_data(engine)

    def test_retired_entry_does_not_use_new_dice_issuer(self):
        self.assertFalse(engine.has_executable_planned_entry('DICE', '2023-09-01'))
        self.assertTrue(engine.has_executable_planned_entry('DICE', '2023-08-01'))

    def test_umpqua_final_trading_session_is_preserved(self):
        self.assertTrue(engine.has_executable_planned_entry('UMPQ', '2023-02-28'))
        self.assertFalse(engine.has_executable_planned_entry('UMPQ', '2023-03-01'))

    def test_eagle_uses_star_bulk_not_reused_etf_symbol(self):
        action=engine.STOCK_CORPORATE_ACTIONS['EGLE']
        self.assertEqual(action['successor_ticker'],'SBLK')
        self.assertAlmostEqual(action['shares_per_share'],2.6211)
        self.assertFalse(engine.has_executable_planned_entry('EGLE','2024-05-01'))

    def test_cash_cvr_is_not_assigned_a_value(self):
        action=engine.CASH_CORPORATE_ACTIONS['ITOS']
        self.assertAlmostEqual(action['cash_per_share'],10.047)
        self.assertNotIn('cvr_value',action)

    def test_ryerson_issuer_not_olympic_merger_exchange_ratio(self):
        self.assertEqual(engine.STOCK_CORPORATE_ACTIONS['RYI']['shares_per_share'],1)
        self.assertEqual(engine.STOCK_CORPORATE_ACTIONS['RYI']['successor_ticker'],'RYZ')
