#!/usr/bin/env python3
"""One-shot validation of the preregistered seasoned durable-liquidity trend candidate."""

import argparse
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

import backtest_momentum_v3 as engine
from verified_exit_data import install_verified_exit_data


MODEL = "seasoned-durable-liquidity-trend-v1"
TOP_N = 12
MIN_PRICE_USD = 5.0
MIN_ADV_USD = 2_000_000.0
HISTORY_SESSIONS = 504
WARMUP_START = "2023-11-01"


def annualized_volatility(closes):
    daily_returns = [
        closes[index] / closes[index + 1] - 1.0
        for index in range(63)
    ]
    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum(
        (value - mean_return) ** 2 for value in daily_returns
    ) / (len(daily_returns) - 1)
    return math.sqrt(variance) * math.sqrt(252.0)


def durable_liquidity_metrics(tickers, latest_map, recent504, _model, _min_adv20_usd):
    """Apply only the rules locked in the v1 preregistration."""
    output = []
    for ticker in tickers:
        latest = engine.get_from_map(latest_map, ticker)
        if not latest:
            continue
        closes, dollar_values = [], []
        for index, (_, grouped) in enumerate(recent504):
            row = engine.get_from_map(grouped, ticker)
            if not row or row.get("volume") is None:
                break
            close = float(row["close"])
            volume = float(row["volume"])
            if close <= 0.0 or volume <= 0.0:
                break
            closes.append(close)
            dollar_values.append(close * volume)
        if len(closes) < HISTORY_SESSIONS:
            continue
        price = float(latest["close"])
        adv20 = sum(dollar_values[:20]) / 20.0
        adv126 = sum(dollar_values[:126]) / 126.0
        sma50 = sum(closes[:50]) / 50.0
        sma200 = sum(closes[:200]) / 200.0
        return126 = closes[0] / closes[126] - 1.0
        volatility = annualized_volatility(closes)
        if (
            price < MIN_PRICE_USD
            or adv20 < MIN_ADV_USD
            or adv126 < MIN_ADV_USD
            or price <= sma200
            or sma50 <= sma200
            or return126 <= 0.0
            or volatility <= 0.0
        ):
            continue
        output.append(SimpleNamespace(
            ticker=ticker,
            price_usd=price,
            total_score=return126 / volatility,
        ))
    return output


def label_outputs(requested_start, effective_start):
    for filename in ("Momentum_backtest_results.csv", "Momentum_backtest_positions.csv"):
        path = Path(filename)
        if path.exists():
            frame = pd.read_csv(path)
            if "SelectionModel" in frame:
                frame["SelectionModel"] = MODEL
            frame.to_csv(path, index=False)
    summary_path = Path("Momentum_backtest_summary.csv")
    if not summary_path.exists():
        raise RuntimeError("Backtest did not produce Momentum_backtest_summary.csv")
    summary = pd.read_csv(summary_path)
    summary["SelectionModel"] = MODEL
    summary["RequestedValidationStart"] = requested_start
    summary["EffectiveWarmupStart"] = effective_start
    summary["SelectionHistorySessions"] = HISTORY_SESSIONS
    summary["LiquidityRule"] = "ADV20_AND_ADV126_MIN_2M_USD"
    summary.to_csv(summary_path, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2023-02-01")
    parser.add_argument(
        "--end",
        default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat(),
    )
    args = parser.parse_args()
    effective_start = max(args.start, WARMUP_START)

    original_metrics = engine.build_prior_2_12_metrics
    original_session_window = engine.session_window

    def seasoned_history(client, cache, tickers, asof, needed=253):
        return original_session_window(
            client,
            cache,
            tickers,
            asof,
            HISTORY_SESSIONS if needed == 253 else needed,
        )

    engine.build_prior_2_12_metrics = durable_liquidity_metrics
    engine.session_window = seasoned_history
    try:
        engine.run(
            effective_start,
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
        label_outputs(args.start, effective_start)
    finally:
        engine.build_prior_2_12_metrics = original_metrics
        engine.session_window = original_session_window


if __name__ == "__main__":
    main()
