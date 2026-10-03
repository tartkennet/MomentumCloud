#!/usr/bin/env python3
"""One-shot point-in-time validation of trend-following persistence 252 v1."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import backtest_momentum_v3 as engine

try:
    import verified_exit_data    verified_exit_data.install_verified_exit_data(engine)
except ImportError:
    pass

MODEL = "trend-following-persistence-252-v1"
OOS_START = "2025-03-31"
TOP_N = 12
HISTORY_SESSIONS = 252
PERSISTENCE_WINDOW = 32
MIN_PERSISTENT_DAYS = 24
MIN_PRICE_USD = 5.0
MIN_ADV_USD = 2_000_000.0


def annualised_volatility(closes: list[float]) -> float:
    returns = [closes[i] / closes[i + 1] - 1.0 for i in range(63)]
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / len(returns)
    return (variance ** 0.5) * (252 ** 0.5)


def persistence_metrics(tickers, latest_map, recent_history, _model, _min_adv20_usd):
    """Build a time-series trend signal, not a momentum-return ranking."""
    metrics = []
    for ticker in tickers:
        latest = engine.get_from_map(latest_map, ticker)
        if not latest:
            continue
        closes, dollar_values = [], []
        for index, (_, grouped) in enumerate(recent_history):
            row = engine.get_from_map(grouped, ticker)
            if not row:
                break
            close = float(row["close"])
            closes.append(close)
            if index < 63 and row.get("volume") is not None:
                dollar_values.append(close * float(row["volume"]))
        if len(closes) < HISTORY_SESSIONS or len(dollar_values) < 63:
            continue
        price = closes[0]
        adv20 = sum(dollar_values[:20]) / 20.0
        adv63 = sum(dollar_values) / 63.0
        sma50 = sum(closes[:50]) / 50.0
        sma200 = sum(closes[:200]) / 200.0
        prior_sma200 = sum(closes[20:220]) / 200.0
        above_sma200_days = 0
        for offset in range(PERSISTENCE_WINDOW):
            rolling_sma200 = sum(closes[offset:offset + 200]) / 200.0
            if closes[offset] > rolling_sma200:
                above_sma200_days += 1
        extension = price / sma50 - 1.0
        if not (
            price >= MIN_PRICE_USD
            and adv20 >= MIN_ADV_USD
            and adv63 >= MIN_ADV_USD
            and price > sma50 > sma200 > prior_sma200
            and above_sma200_days >= MIN_PERSISTENT_DAYS
            and extension <= 0.08
        ):
            continue
        score = float(above_sma200_days) - annualised_volatility(closes) / 1000.0
        metrics.append(SimpleNamespace(ticker=ticker, price_usd=price, total_score=score))
    return metrics


def segment_metrics(results: pd.DataFrame, positions: pd.DataFrame, cache: dict) -> dict:
    if results.empty:
        raise RuntimeError("Validation segment contains no complete monthly periods")
    portfolio_index = (1 + results["NetReturn_pct"] / 100).prod()
    spy_index = (1 + results["SPYReturn_pct"] / 100).prod()
    daily_drawdown = engine.daily_portfolio_max_drawdown(
        positions.to_dict("records"), cache, sorted(cache)
    )
    total_return = (portfolio_index - 1) * 100
    spy_return = (spy_index - 1) * 100
    return {
        "Periods": int(len(results)),
        "TotalReturn_pct": total_return,
        "SPYTotalReturn_pct": spy_return,
        "TotalEdgeVsSPY_pct": total_return - spy_return,
        "PeriodHitRate_pct": float((results["NetReturn_pct"] > 0).mean() * 100),
        "DailyMaxDrawdown_pct": float(daily_drawdown),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2023-02-01")
    parser.add_argument(
        "--end", default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    )
    args = parser.parse_args()
    original_builder = engine.build_prior_2_12_metrics
    original_window = engine.session_window

    def wide_session_window(client, cache, tickers, asof, needed=253):
        return original_window(client, cache, tickers, asof, needed=HISTORY_SESSIONS)

    engine.build_prior_2_12_metrics = persistence_metrics
    engine.session_window = wide_session_window
    try:
        engine.run(
            start=args.start,
            end=args.end,
            rebalance_months=1,
            stop_loss_pct=None,
            exit_rule="sma50",
            exit_execution="next-open",
            top_n=TOP_N,
            entry_execution="next-open",
            rebalance_exit_execution="next-open",
            selection_model="v6-core",
            portfolio_value_usd=10_000,
            universe_mode="point-in-time",
        )
    except RuntimeError as error:
        blocked = {
            "model": MODEL,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "status": "BLOCKED",
            "reason": "validation_execution_blocked",
            "error": str(error),
            "out_of_sample_start": OOS_START,
            "metrics": None,
            "out_of_sample_metrics": None,
            "limitation": "Current limitation: survivorship bias",
        }
        Path("Momentum_trend_following_persistence_validation_decision.json").write_text(
            json.dumps(blocked, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        raise
    finally:
        engine.build_prior_2_12_metrics = original_builder
        engine.session_window = original_window

    results = pd.read_csv("Momentum_backtest_results.csv")
    positions = pd.read_csv("Momentum_backtest_positions.csv")
    summary = pd.read_csv("Momentum_backtest_summary.csv")
    for frame in (results, positions, summary):
        frame["SelectionModel"] = MODEL
    results.to_csv("Momentum_backtest_results.csv", index=False)
    positions.to_csv("Momentum_backtest_positions.csv", index=False)
    summary.to_csv("Momentum_backtest_summary.csv", index=False)

    cache_payload = json.loads(Path(engine.CACHE_FILE).read_text(encoding="utf-8"))
    cache = cache_payload["sessions"]
    metrics = summary.iloc[0].to_dict()
    oos_results = results.loc[results["SignalDate"] >= OOS_START].copy()
    oos_positions = positions.loc[positions["SignalDate"] >= OOS_START].copy()
    oos = segment_metrics(oos_results, oos_positions, cache)
    gates = {
        "at_least_30_periods": int(metrics["Periods"]) >= 30,
        "positive_net_return": float(metrics["TotalReturn_pct"]) > 0,
        "beats_spy": float(metrics["TotalEdgeVsSPY_pct"]) > 0,
        "daily_max_drawdown_at_most_20_pct": float(metrics["DailyMaxDrawdown_pct"]) >= -20,
        "hit_rate_at_least_50_pct": float(metrics["PeriodHitRate_pct"]) >= 50,
        "oos_at_least_12_periods": int(oos["Periods"]) >= 12,
        "oos_positive_net_return": oos["TotalReturn_pct"] > 0,
        "oos_beats_spy": oos["TotalEdgeVsSPY_pct"] > 0,
        "oos_daily_max_drawdown_at_most_20_pct": oos["DailyMaxDrawdown_pct"] >= -20,
        "oos_hit_rate_at_least_50_pct": oos["PeriodHitRate_pct"] >= 50,
    }
    decision = {
        "model": MODEL,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "universe": metrics["Universe"],
        "out_of_sample_start": OOS_START,
        "status": "GO" if all(gates.values()) else "NO-GO",
        "gates": gates,
        "metrics": {key: metrics[key] for key in (
            "Periods", "TotalReturn_pct", "SPYTotalReturn_pct", "TotalEdgeVsSPY_pct",
            "DailyMaxDrawdown_pct", "PeriodHitRate_pct", "CashPeriods",
            "DataQualityExclusionCount",
        )},
        "out_of_sample_metrics": oos,
        "limitation": "Current limitation: survivorship bias",
    }
    Path("Momentum_trend_following_persistence_validation_decision.json").write_text(
        json.dumps(decision, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    if decision["status"] != "GO":
        failed = ", ".join(name for name, passed in gates.items() if not passed)
        raise RuntimeError(f"Trend-following persistence 252 v1 is NO-GO: {failed}")
    print("MomentumCloud trend-following persistence 252 v1: GO")


if __name__ == "__main__":
    main()
