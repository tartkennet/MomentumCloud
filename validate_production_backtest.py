#!/usr/bin/env python3
"""Run the single locked MomentumCloud Production v1 validation."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import pandas as pd

from backtest_momentum_v3 import run
from momentum_config import PRODUCTION


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the locked production model")
    parser.add_argument(
        "--start",
        default=(datetime.now(timezone.utc).date() - timedelta(days=365 * 5)).isoformat(),
    )
    parser.add_argument(
        "--end",
        default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat(),
    )
    args = parser.parse_args()
    run(
        start=args.start,
        end=args.end,
        rebalance_months=1,
        stop_loss_pct=PRODUCTION.stop_loss_pct,
        exit_rule="stop",
        exit_execution="next-open",
        top_n=PRODUCTION.position_count,
        entry_execution="next-open",
        rebalance_exit_execution="next-open",
        selection_model=PRODUCTION.selection_model,
        portfolio_value_usd=10_000.0,
        universe_mode="current-template",
    )
    summary = pd.read_csv("Momentum_backtest_summary.csv").iloc[0].to_dict()
    expected = {
        "RebalanceMonths": 1,
        "TopN": 15,
        "SelectionModel": "v4-balanced",
        "LiquidityRule": "FIXED_MIN_ADV20_5M_USD",
        "EffectiveMinADV20_USD": 5_000_000.0,
        "EntryExecution": "next-open",
        "ExitExecution": "next-open",
        "RebalanceExitExecution": "next-open",
        "StopLoss_pct": 10.0,
        "Universe": "CURRENT_TEMPLATE_SURVIVORSHIP_BIAS",
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise RuntimeError(f"Locked production mismatch: {key}={summary.get(key)!r}, expected {value!r}")
    print("MomentumCloud Production v1 backtest configuration verified")


if __name__ == "__main__":
    main()

