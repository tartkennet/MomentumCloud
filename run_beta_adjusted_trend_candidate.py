#!/usr/bin/env python3
"""One-shot validation of the pre-registered beta-adjusted trend candidate."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import backtest_momentum_v3 as engine
from momentum_config import PRODUCTION
from validate_production_backtest import segment_metrics

MODEL = "beta-adjusted-trend-v1"
OOS_START = "2025-03-31"
TOP_N = 15
STOP_LOSS_PCT = 10.0

def beta_adjusted_metrics(tickers, latest_map, recent253, _model, min_adv20_usd):
    spy = []
    for _, grouped in recent253:
        row = engine.get_from_map(grouped, "SPY")
        if not row:
            break
        spy.append(float(row["close"]))
    if len(spy) < 253:
        return []
    spy_mom = (spy[21] / spy[252] - 1.0) * 100.0
    spy_path = list(reversed(spy[21:253]))
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
        if len(closes) < 253 or len(dollars) < 10:
            continue
        price = float(latest["close"])
        stock_path = list(reversed(closes[21:253]))
        pairs = [(b / a - 1.0, d / c - 1.0) for a, b, c, d in zip(stock_path, stock_path[1:], spy_path, spy_path[1:]) if a > 0 and b > 0 and c > 0 and d > 0]
        if len(pairs) < 200:
            continue
        stock_mean = sum(x for x, _ in pairs) / len(pairs)
        spy_mean = sum(x for _, x in pairs) / len(pairs)
        spy_variance = sum((x - spy_mean) ** 2 for _, x in pairs)
        if spy_variance <= 0:
            continue
        beta = sum((x - stock_mean) * (y - spy_mean) for x, y in pairs) / spy_variance
        score = (closes[21] / closes[252] - 1.0) * 100.0 - beta * spy_mom
        if price < PRODUCTION.min_price_usd or sum(dollars) / len(dollars) < min_adv20_usd or price <= sum(closes[:200]) / 200.0 or score <= 0:
            continue
        output.append(SimpleNamespace(ticker=ticker, price_usd=price, total_score=score))
    return output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2023-02-01")
    parser.add_argument("--end", default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat())
    args = parser.parse_args()
    original = engine.build_prior_2_12_metrics
    engine.build_prior_2_12_metrics = beta_adjusted_metrics
    try:
        # v6-core supplies only unchanged SPY/SMA200 regime and execution mechanics.
        engine.run(args.start, args.end, 1, STOP_LOSS_PCT, "stop", "next-open", TOP_N, "next-open", "next-open", "v6-core", 10_000.0, "point-in-time")
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
        "positive_net_return": float(metrics["TotalReturn_pct"]) > 0,
        "beats_spy": float(metrics["TotalEdgeVsSPY_pct"]) > 0,
        "daily_max_drawdown_at_most_20_pct": float(metrics["DailyMaxDrawdown_pct"]) >= -20,
        "hit_rate_at_least_50_pct": float(metrics["PeriodHitRate_pct"]) >= 50,
        "oos_at_least_12_periods": int(oos["Periods"]) >= 12,
        "oos_positive_net_return": oos["TotalReturn_pct"] > 0,
        "oos_beats_spy": oos["TotalEdgeVsSPY_pct"] > 0,
        "oos_hit_rate_at_least_50_pct": oos["PeriodHitRate_pct"] >= 50,
    }
    decision = {"model": MODEL, "validated_at": datetime.now(timezone.utc).isoformat(), "universe": metrics["Universe"], "out_of_sample_start": OOS_START, "status": "GO" if all(gates.values()) else "NO-GO", "gates": gates, "metrics": {key: metrics[key] for key in ("Periods", "TotalReturn_pct", "SPYTotalReturn_pct", "TotalEdgeVsSPY_pct", "DailyMaxDrawdown_pct", "PeriodHitRate_pct", "CashPeriods", "DataQualityExclusionCount")}, "out_of_sample_metrics": oos, "limitation": "Current limitation: survivorship bias"}
    Path("Momentum_beta_adjusted_trend_validation_decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    if decision["status"] != "GO":
        raise RuntimeError("Beta-adjusted trend v1 is NO-GO: " + ", ".join(name for name, passed in gates.items() if not passed))

if __name__ == "__main__":
    main()
