"""Check the locked model's actual portfolio decisions across both callers."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import backtest_momentum_v3 as backtest
from momentum_config import PRODUCTION
from momentum_strategy import market_regime, rank_universe


class RobustBacktestParityTests(unittest.TestCase):
    def test_dwac_keeps_its_original_symbol_until_market_effective_date(self):
        from audit_dated_action_chain import identity
        self.assertEqual(identity(backtest.STOCK_CORPORATE_ACTIONS, 'DWAC', '2024-03-25', '2024-03-01'), ('DWAC', 1.0, None))
        successor, ratio, action = identity(backtest.STOCK_CORPORATE_ACTIONS, 'DWAC', '2024-03-26', '2024-03-01')
        self.assertEqual((successor, ratio), ('DJT', 1.0))
        self.assertEqual(action['effective_date'], '2024-03-26')

    def test_ranking_and_data_guards_match_live(self):
        rising = [150.0 - i * 50.0 / 252 for i in range(253)]
        history = []
        for i, close in enumerate(rising):
            grouped = {ticker: {"close": close, "volume": 100_000.0}
                       for ticker in ("AAA", "BBB", "MISSING_VOLUME", "BROKEN_SPLIT")}
            grouped["SPY"] = {"close": close, "volume": 1_000_000.0}
            if i == 0:
                grouped["MISSING_VOLUME"].pop("volume")
            if i == 100:
                grouped["BROKEN_SPLIT"]["close"] /= 4.0
            history.append((str(i), grouped))
        tickers = ["BBB", "MISSING_VOLUME", "BROKEN_SPLIT", "AAA"]
        expected = rank_universe(tickers, history)
        actual = backtest.build_prior_2_12_metrics(
            tickers, history[0][1], history, PRODUCTION.selection_model,
            PRODUCTION.min_adv20_usd,
        )
        self.assertEqual([r.ticker for r in actual], [r.ticker for r in expected])
        self.assertEqual([r.total_score for r in actual], [r.score for r in expected])
        self.assertEqual([r.price_usd for r in actual], [r.price_usd for r in expected])

    def test_spy_regime_matches_live_for_risk_on_off_and_missing_history(self):
        cases = {
            "above_sma": [101.0] + [100.0] * 252,
            "below_sma": [99.0] + [100.0] * 252,
            "at_sma": [100.0] * 253,
            "missing_history": [101.0] * 199,
            "missing_spy": [],
        }
        candidate = SimpleNamespace(ticker="QUALIFIED", total_score=100.0)
        for name, closes in cases.items():
            with self.subTest(name=name):
                history = [(str(i), {"SPY": {"close": close}})
                           for i, close in enumerate(closes)]
                signal_map = history[0][1] if history else {}
                expected = [candidate] if market_regime(history)["risk_on"] else []
                with patch.object(backtest, "session_window", return_value=history), patch.object(
                    backtest, "build_prior_2_12_metrics", return_value=[candidate]
                ) as builder:
                    actual = backtest.choose_top(
                        None, {"signal": signal_map}, ["QUALIFIED"], "signal",
                        PRODUCTION.position_count,
                        selection_model=PRODUCTION.selection_model,
                        min_adv20_usd=PRODUCTION.min_adv20_usd,
                    )
                self.assertEqual(actual, expected)
                self.assertEqual(builder.call_count, int(bool(expected)))


if __name__ == "__main__":
    unittest.main()
