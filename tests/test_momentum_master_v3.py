import unittest

from momentum_master_v3 import simple_moving_average


class SimpleMovingAverageTests(unittest.TestCase):
    def test_uses_latest_trading_sessions(self):
        closes = [float(value) for value in range(253, 0, -1)]

        self.assertEqual(simple_moving_average(closes, 50), 228.5)
        self.assertEqual(simple_moving_average(closes, 200), 153.5)

    def test_requires_enough_history(self):
        self.assertIsNone(simple_moving_average([10.0] * 49, 50))


if __name__ == "__main__":
    unittest.main()
