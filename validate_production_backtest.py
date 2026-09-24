#!/usr/bin/env python3
"""Run the single locked MomentumCloud Production v1 validation."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
        universe_mode="point-in-time",
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
        "Universe": "POINT_IN_TIME_US_COMMON_STOCKS",
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise RuntimeError(f"Locked production mismatch: {key}={summary.get(key)!r}, expected {value!r}")
    gates = {
        "at_least_30_periods": int(summary["Periods"]) >= 30,
        "positive_net_return": float(summary["TotalReturn_pct"]) > 0.0,
        "beats_spy": float(summary["TotalEdgeVsSPY_pct"]) > 0.0,
        "daily_max_drawdown_at_most_20_pct": float(summary["DailyMaxDrawdown_pct"]) >= -20.0,
        "hit_rate_at_least_50_pct": float(summary["PeriodHitRate_pct"]) >= 50.0,
    }
    decision = {
        "model": PRODUCTION.selection_model,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "universe": summary["Universe"],
        "status": "GO" if all(gates.values()) else "NO-GO",
        "gates": gates,
        "metrics": {
            key: summary[key]
            for key in (
                "Periods", "TotalReturn_pct", "SPYTotalReturn_pct",
                "TotalEdgeVsSPY_pct", "DailyMaxDrawdown_pct",
                "PeriodHitRate_pct",
            )
        },
    }
    Path("Momentum_validation_decision.json").write_text(
        json.dumps(decision, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    if decision["status"] != "GO":
        failed = ", ".join(name for name, passed in gates.items() if not passed)
        raise RuntimeError(f"Production model is NO-GO: {failed}")
    print("MomentumCloud Production v1 point-in-time validation: GO")


if __name__ == "__main__":
    main()
