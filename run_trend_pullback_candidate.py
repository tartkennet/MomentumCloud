#!/usr/bin/env python3
"""One-shot validation of the preregistered regression-trend candidate."""
import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

import backtest_momentum_v3 as engine
from momentum_config import PRODUCTION
from validate_production_backtest import segment_metrics
from verified_exit_data import install_verified_exit_data

MODEL = "regression-trend-persistence-v1"
OOS_START = "2025-03-31"
TOP_N = 10
TREND_WINDOW = 100


def regression_trend_score(closes):
    """Annualised fitted log-price slope times its completed-window R-squared."""
    y_values = list(reversed([math.log(value) for value in closes[:TREND_WINDOW]]))
    x_values = list(range(TREND_WINDOW))
    x_mean = sum(x_values) / TREND_WINDOW
    y_mean = sum(y_values) / TREND_WINDOW
    denominator = sum((value - x_mean) ** 2 for value in x_values)
    slope = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values)
    ) / denominator
    fitted = [y_mean + slope * (value - x_mean) for value in x_values]
    total_variation = sum((value - y_mean) ** 2 for value in y_values)
    residual_variation = sum(
        (value - fit) ** 2 for value, fit in zip(y_values, fitted)
    )
    r_squared = 0.0 if total_variation <= 0.0 else max(
        0.0, 1.0 - residual_variation / total_variation
    )
    annualised_slope_pct = math.expm1(slope * 252.0) * 100.0
    return annualised_slope_pct, r_squared


def regression_trend_metrics(tickers, latest_map, recent253, _model, min_adv20_usd):
    output = []
    for ticker in tickers:
        latest = engine.get_from_map(latest_map, ticker)
        if not latest:
            continue
        closes, dollars = [], []
        for index, (_, grouped) in enumerate(recent253):
            row = engine.get_from_map(grouped, ticker)
            if not row:
                break
            close = float(row["close"])
            if close <= 0.0:
                break
            closes.append(close)
            if index < 20 and row.get("volume") is not None:
                dollars.append(close * float(row["volume"]))
        if len(closes) < 253 or len(dollars) < 20:
            continue
        price = float(latest["close"])
        adv20 = sum(dollars) / len(dollars)
        annualised_slope_pct, r_squared = regression_trend_score(closes)
        if (
            price < PRODUCTION.min_price_usd
            or adv20 < min_adv20_usd
            or annualised_slope_pct <= 0.0
        ):
            continue
        output.append(SimpleNamespace(
            ticker=ticker,
            price_usd=price,
            total_score=annualised_slope_pct * r_squared,
        ))
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2023-02-01")
    parser.add_argument(
        "--end",
        default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat(),
    )
    args = parser.parse_args()

    original_metrics = engine.build_prior_2_12_metrics
    original_drawdown = engine.daily_portfolio_max_drawdown
    daily_context = {}

    def capture_daily_drawdown(position_rows, cache, trading_day_strings):
        daily_context["cache"] = cache
        daily_context["trading_day_strings"] = trading_day_strings
        return original_drawdown(position_rows, cache, trading_day_strings)

    engine.build_prior_2_12_metrics = regression_trend_metrics
    engine.daily_portfolio_max_drawdown = capture_daily_drawdown
    try:
        engine.run(
            args.start,
            args.end,
            1,
            None,
            "rebalance",
            "next-open",
            TOP_N,
            "next-open",
            "next-open",
            "quality-momentum-v2",
            10_000.0,
            "point-in-time",
        )
    finally:
        engine.build_prior_2_12_metrics = original_metrics
        engine.daily_portfolio_max_drawdown = original_drawdown

    if not daily_context:
        raise RuntimeError("Missing daily valuation context for OOS drawdown")

    results = pd.read_csv("Momentum_backtest_results.csv")
    positions = pd.read_csv("Momentum_backtest_positions.csv")
    summary = pd.read_csv("Momentum_backtest_summary.csv")
    for frame in (results, positions, summary):
        frame["SelectionModel"] = MODEL
    results.to_csv("Momentum_backtest_results.csv", index=False)
    positions.to_csv("Momentum_backtest_positions.csv", index=False)
    summary.to_csv("Momentum_backtest_summary.csv", index=False)

    metrics = summary.iloc[0].to_dict()
    oos_results = results.loc[results["SignalDate"].astype(str) >= OOS_START].copy()
    oos = segment_metrics(oos_results)
    oos_positions = positions.loc[
        positions["SignalDate"].astype(str) >= OOS_START
    ].to_dict("records")
    oos_trading_days = [
        day for day in daily_context["trading_day_strings"] if day >= OOS_START
    ]
    oos_daily_drawdown = original_drawdown(
        oos_positions, daily_context["cache"], oos_trading_days
    )
    oos["DailyMaxDrawdown_pct"] = oos_daily_drawdown

    gates = {
        "at_least_30_periods": int(metrics["Periods"]) >= 30,
        "positive_net_return": float(metrics["TotalReturn_pct"]) > 0.0,
        "beats_spy": float(metrics["TotalEdgeVsSPY_pct"]) > 0.0,
        "daily_max_drawdown_at_most_20_pct": float(metrics["DailyMaxDrawdown_pct"]) >= -20.0,
        "hit_rate_at_least_50_pct": float(metrics["PeriodHitRate_pct"]) >= 50.0,
        "oos_at_least_12_periods": int(oos["Periods"]) >= 12,
        "oos_positive_net_return": float(oos["TotalReturn_pct"]) > 0.0,
        "oos_beats_spy": float(oos["TotalEdgeVsSPY_pct"]) > 0.0,
        "oos_daily_max_drawdown_at_most_20_pct": float(oos["DailyMaxDrawdown_pct"]) >= -20.0,
        "oos_hit_rate_at_least_50_pct": float(oos["PeriodHitRate_pct"]) >= 50.0,
    }
    decision = {
        "model": MODEL,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "universe": metrics["Universe"],
        "out_of_sample_start": OOS_START,
        "status": "GO" if all(gates.values()) else "NO-GO",
        "gates": gates,
        "metrics": {
            key: metrics[key]
            for key in (
                "Periods", "TotalReturn_pct", "SPYTotalReturn_pct",
                "TotalEdgeVsSPY_pct", "DailyMaxDrawdown_pct",
                "PeriodHitRate_pct", "CashPeriods", "DataQualityExclusionCount",
            )
        },
        "out_of_sample_metrics": oos,
        "limitation": "Current limitation: survivorship bias",
    }
    serialized = json.dumps(
        decision, indent=2, allow_nan=False, default=lambda value: value.item()
    )
    Path("Momentum_trend_pullback_validation_decision.json").write_text(
        serialized + "\n", encoding="utf-8"
    )
    print(serialized)
    if decision["status"] != "GO":
        failed = ", ".join(name for name, passed in gates.items() if not passed)
        raise RuntimeError(f"Regression-trend persistence v1 is NO-GO: {failed}")


if __name__ == "__main__":
    main()
