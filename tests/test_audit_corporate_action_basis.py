import unittest
from audit_corporate_action_basis import adjustment_factor, convert_stock_row


class CorporateActionBasisTests(unittest.TestCase):
    def test_successor_future_reverse_split_preserves_legal_ratio(self):
        self.assertAlmostEqual(convert_stock_row({"open": 114.10}, 1, 0, 1, 10)["open"], 11.41)

    def test_cash_and_stock_original_units(self):
        self.assertAlmostEqual(convert_stock_row({"open": 100}, .5, 9, 2, 4)["open"], 43)

    def test_equal_basis(self):
        self.assertEqual(convert_stock_row({"open": 80}, 1, 0, .5, .5)["open"], 80)

    def test_invalid_basis(self):
        for value in (0, -1, float("nan")):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                adjustment_factor(value, 1)
