#!/usr/bin/env python3
"""One-shot validation of the pre-registered trend-pullback candidate."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import backtest_momentum_v3 as engine
from momentum_config import PRODUCTION
from validate_production_backtest import segment_metrics

MODEL = "trend-pullback-v1"
OOS_START = "2025-03-31"
TOP_N = 15
STOP_LOSS_PCT = 10.0


def trend_pullback_metrics(tickers, latest_map, recent253, _model, min_adv20_usd):
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
            closes.append(close)
            if index < 20 and row.get("volume") is not None:
                dollars.append(close * float(row["volume"]))
        if len(closes) < 253 or len(dollars) < 20:
            continue
        price = float(latest["close"])
        sma50 = sum(closes[:50]) / 50.0
        sma200 = sum(closes[:200]) / 200.0
        prior_sma200 = sum(closes[20:220]) / 200.0
        extension_pct = (price / sma50 - 1.0) * 100.0
        trend_spread_pct = (sma50 / sma200 - 1.0) * 100.0
        if (
            price < PRODUCTION.min_price_usd
            or sum(dollars) / len(dollars) < min_adv20_usd
            or price <= sma200
            or sma50 <= sma200
            or sma200 <= prior_sma200
            or extension_pct < 0.0
            or extension_pct > 10.0
        ):
            continue
        score = trend_spread_pct * (1.0 - extension_pct / 10.0)
        if score <= 0.0:
            continue
        output.append(SimpleNamespace(ticker=ticker, price_usd=price, total_score=score))
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2023-02-01")
    parser.add_argument("--end", default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat())
    args = parser.parse_args()
    original = engine.build_prior_2_12_metrics
    engine.build_prior_2_12_metrics = trend_pullback_metrics
    try:
        engine.run(args.start, args.end, 1, STOP_LOSS_PCT, "stop", "next-open", TOP_N, "next-open", "next-open", "quality-momentum-v2", 10_000.0, "point-in-time")
    finally:
        engine.build_prior_2_12_metrics = original
    results = pd.read_csv("Momentum_backtest_results.csv")
    positions = pd.read_csv("Momentum_backtest_positions.csv")
    summary = pd.read_csv("Momentum_backtest_summary.csv")
    for frame in (results, positions, summary):
        frame["SelectionModel"] = MODEL
    results.to_csv("Momentum_backtest_results.csv", index=False)
    positions.to_csv("Momentum_backtest_positions.csv", index=False)
    summary.to_csv("Momentum_backtest_summary.csv", index=False)
    metrics = summary.iloc[0].to_dict()
    oos = segment_metrics(results.loc[results["SignalDate"] >= OOS_START].copy())
    gates = {
        "at_least_30_periods": int(metrics["Periods"]) >= 30,
        "positive_net_return": float(metrics["TotalReturn_pct"]) > 0.0,
        "beats_spy": float(metrics["TotalEdgeVsSPY_pct"]) > 0.0,
        "daily_max_drawdown_at_most_20_pct": float(metrics["DailyMaxDrawdown_pct"]) >= -20.0,
        "hit_rate_at_least_50_pct": float(metrics["PeriodHitRate_pct"]) >= 50.0,
        "oos_at_least_12_periods": int(oos["Periods"]) >= 12,
        "oos_positive_net_return": oos["TotalReturn_pct"] > 0.0,
        "oos_beats_spy": oos["TotalEdgeVsSPY_pct"] > 0.0,
        "oos_hit_rate_at_least_50_pct": oos["PeriodHitRate_pct"] >= 50.0,
    }
    decision = {
        "model": MODEL,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "universe": metrics["Universe"],
        "out_of_sample_start": OOS_START,
        "status": "GO" if all(gates.values()) else "NO-GO",
        "gates": gates,
        "metrics": {key: metrics[key] for key in ("Periods", "TotalReturn_pct", "SPYTotalReturn_pct", "TotalEdgeVsSPY_pct", "DailyMaxDrawdown_pct", "PeriodHitRate_pct", "CashPeriods", "DataQualityExclusionCount")},
        "out_of_sample_metrics": oos,
        "limitation": "Current limitation: survivorship bias",
    }
    Path("Momentum_trend_pullback_validation_decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if decision["status"] != "GO":
        raise RuntimeError("Trend-pullback v1 is NO-GO: " + ", ".join(name for name, passed in gates.items() if not passed))


if __name__ == "__main__":
    main()
