#!/usr/bin/env python3
"""Run the locked robust-momentum validation with an untouched OOS segment."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from backtest_momentum_v3 import run
from momentum_config import PRODUCTION


OOS_START = "2025-03-31"
# Pre-registered PR 13 exit rule: a fixed 10% stop, with no additional
# single-stock moving-average exit. SPY>SMA200 remains the market-wide
# risk-off rule.
VALIDATION_EXIT_RULE = "stop"


def segment_metrics(results: pd.DataFrame) -> dict:
    """Compound exactly the rows belonging to one chronological segment."""
    if results.empty:
        raise RuntimeError("Validation segment contains no complete monthly periods")
    portfolio_index = (1.0 + results["NetReturn_pct"] / 100.0).prod()
    spy_index = (1.0 + results["SPYReturn_pct"] / 100.0).prod()
    total_return = (portfolio_index - 1.0) * 100.0
    spy_return = (spy_index - 1.0) * 100.0
    return {
        "Periods": int(len(results)),
        "TotalReturn_pct": total_return,
        "SPYTotalReturn_pct": spy_return,
        "TotalEdgeVsSPY_pct": total_return - spy_return,
        "PeriodHitRate_pct": float((results["NetReturn_pct"] > 0.0).mean() * 100.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the locked production model")
    parser.add_argument(
        "--start",
        # Starter exposes five years.  The ranking needs 253 trading sessions,
        # which is approximately 450 calendar days with exchange holidays.
        # Keep a provider-access buffer as well, rather than silently issuing
        # a partial-history test near the entitlement boundary.
        # Fixed before the model run.  Together with the 450-calendar-day
        # formation buffer it stays within Starter's five-year entitlement.
        default="2023-02-01",
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
        exit_rule=VALIDATION_EXIT_RULE,
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
        "TopN": PRODUCTION.position_count,
        "SelectionModel": PRODUCTION.selection_model,
        "LiquidityRule": "FIXED_MIN_ADV20_2M_USD",
        "EffectiveMinADV20_USD": 2_000_000.0,
        "EntryExecution": "next-open",
        "ExitExecution": "next-open",
        "RebalanceExitExecution": "next-open",
        "ExitRule": VALIDATION_EXIT_RULE,
        "StopLoss_pct": 10.0,
        "Universe": "POINT_IN_TIME_US_COMMON_STOCKS",
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise RuntimeError(f"Locked production mismatch: {key}={summary.get(key)!r}, expected {value!r}")
    results = pd.read_csv("Momentum_backtest_results.csv")
    oos = results.loc[results["SignalDate"] >= OOS_START].copy()
    oos_metrics = segment_metrics(oos)
    gates = {
        "at_least_30_periods": int(summary["Periods"]) >= 30,
        "positive_net_return": float(summary["TotalReturn_pct"]) > 0.0,
        "beats_spy": float(summary["TotalEdgeVsSPY_pct"]) > 0.0,
        "daily_max_drawdown_at_most_20_pct": float(summary["DailyMaxDrawdown_pct"]) >= -20.0,
        "hit_rate_at_least_50_pct": float(summary["PeriodHitRate_pct"]) >= 50.0,
        "oos_at_least_12_periods": int(oos_metrics["Periods"]) >= 12,
        "oos_positive_net_return": float(oos_metrics["TotalReturn_pct"]) > 0.0,
        "oos_beats_spy": float(oos_metrics["TotalEdgeVsSPY_pct"]) > 0.0,
        "oos_hit_rate_at_least_50_pct": float(oos_metrics["PeriodHitRate_pct"]) >= 50.0,
    }
    decision = {
        "model": PRODUCTION.selection_model,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "universe": summary["Universe"],
        "out_of_sample_start": OOS_START,
        "status": "GO" if all(gates.values()) else "NO-GO",
        "gates": gates,
        "metrics": {
            key: summary[key]
            for key in (
                "Periods", "TotalReturn_pct", "SPYTotalReturn_pct",
                "TotalEdgeVsSPY_pct", "DailyMaxDrawdown_pct",
            "PeriodHitRate_pct",
            "CashPeriods", "DataQualityExclusionCount",
        )
        },
        "out_of_sample_metrics": oos_metrics,
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
