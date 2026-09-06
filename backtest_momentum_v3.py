#!/usr/bin/env python3
"""Point-in-time Momentum v3 backtest. Does not alter the daily BuyNow run."""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from momentum_master_v3 import (
    INPUT_TEMPLATE,
    PolygonClient,
    build_metrics,
    get_from_map,
    load_history_cache,
    read_universe,
    save_history_cache,
    slim_grouped_map,
)

CACHE_FILE = ".momentum_backtest_cache.json"
TOP10 = 10
ROUND_TRIP_COST_PCT = 0.30


def trading_dates(client, end_date, count, cache=None):
    """Return recent trading sessions, reusing the persistent history cache."""
    cache = cache or {}
    dates, day = [], end_date
    while len(dates) < count:
        if day.weekday() < 5:
            date_string = day.isoformat()
            if date_string in cache:
                dates.append((date_string, cache[date_string]))
            else:
                grouped = client.fetch_grouped_stocks(date_string)
                if len(grouped) > 1000:
                    dates.append((date_string, grouped))
        day -= timedelta(days=1)
    return list(reversed(dates))


def calendar_rebalance_signals(trading_day_strings, start, end, rebalance_months):
    """First available session in every Nth calendar month, starting at start."""
    eligible = [day for day in trading_day_strings if start <= day <= end]
    first_by_month = {}
    for day in eligible:
        first_by_month.setdefault(day[:7], day)
    return [first_by_month[month] for month in sorted(first_by_month)[::rebalance_months]]


def execution_periods(trading_day_strings, signals, end):
    """Use signal close, then enter at the next session close to prevent look-ahead."""
    sessions = [day for day in trading_day_strings if day <= end]
    positions = {day: index for index, day in enumerate(sessions)}
    usable = [signal for signal in signals if positions.get(signal, len(sessions)) + 1 < len(sessions)]
    periods = []
    for index, signal in enumerate(usable):
        entry = sessions[positions[signal] + 1]
        if index + 1 < len(usable):
            next_signal = usable[index + 1]
            exit_day = sessions[positions[next_signal] + 1]
        else:
            exit_day = sessions[-1]
        if entry < exit_day:
            periods.append((signal, entry, exit_day))
    return periods


def rebalance_point_max_drawdown(index_values):
    """Maximum drawdown measured at the available portfolio valuation points."""
    peak = 100.0
    worst = 0.0
    for value in index_values:
        peak = max(peak, float(value))
        worst = min(worst, float(value) / peak - 1.0)
    return worst * 100.0


def session_window(client, cache, tickers, asof, needed=253):
    if asof not in cache:
        cache[asof] = slim_grouped_map(client.fetch_grouped_stocks(asof), tickers)
    day = datetime.fromisoformat(asof).date()
    while len([date for date in cache if date <= asof]) < needed:
        if day.weekday() < 5:
            date_string = day.isoformat()
            if date_string not in cache:
                grouped = client.fetch_grouped_stocks(date_string)
                if len(grouped) > 1000:
                    cache[date_string] = slim_grouped_map(grouped, tickers)
        day -= timedelta(days=1)
    dates = sorted((date for date in cache if date <= asof), reverse=True)[:needed]
    return [(date, cache[date]) for date in dates]


def choose_top10(client, cache, tickers, asof):
    signal_map = cache.get(asof)
    if signal_map is None:
        signal_map = slim_grouped_map(client.fetch_grouped_stocks(asof), tickers)
        cache[asof] = signal_map
    history = session_window(client, cache, tickers, asof)
    metrics, _, _ = build_metrics(tickers, signal_map, history)
    return sorted(metrics, key=lambda item: item.total_score, reverse=True)[:TOP10]


def run(start, end, rebalance_months):
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("Missing POLYGON_API_KEY")
    client = PolygonClient(api_key)
    tickers = read_universe(INPUT_TEMPLATE)
    history_tickers = list(dict.fromkeys(tickers + ["SPY"]))
    cache = load_history_cache(CACHE_FILE)
    start_day = datetime.fromisoformat(start).date()
    end_day = datetime.fromisoformat(end).date()
    if start_day >= end_day:
        raise ValueError("start must be earlier than end")

    needed_sessions = 253 + int((end_day - start_day).days * 5 / 7) + 10
    all_days = trading_dates(client, end_day, needed_sessions, cache=cache)
    for date_string, grouped in all_days:
        cache[date_string] = slim_grouped_map(grouped, history_tickers)
    save_history_cache(CACHE_FILE, [(date, cache[date]) for date in cache])

    trading_day_strings = [date for date, _ in all_days]
    signals = calendar_rebalance_signals(trading_day_strings, start, end, rebalance_months)
    periods = execution_periods(trading_day_strings, signals, end)
    if not periods:
        raise RuntimeError("No executable rebalance periods in requested range")

    rows, position_rows, equity, spy_equity = [], [], 1.0, 1.0
    for signal, entry, exit_day in periods:
        picks = choose_top10(client, cache, tickers, signal)
        if len(picks) < TOP10:
            raise RuntimeError(f"Only {len(picks)} qualified names on {signal}")
        entry_map = cache[entry]
        exit_map = cache[exit_day]
        stock_returns = []
        for rank, pick in enumerate(picks, start=1):
            entry_row = get_from_map(entry_map, pick.ticker)
            exit_row = get_from_map(exit_map, pick.ticker)
            if entry_row and exit_row:
                stock_return = float(exit_row["close"]) / float(entry_row["close"]) - 1
                stock_returns.append(stock_return)
                position_rows.append({
                    "SignalDate": signal,
                    "EntryDate": entry,
                    "ExitDate": exit_day,
                    "RebalanceMonths": rebalance_months,
                    "Rank": rank,
                    "Ticker": pick.ticker,
                    "SignalPrice_USD": pick.price_usd,
                    "EntryPrice_USD": float(entry_row["close"]),
                    "ExitPrice_USD": float(exit_row["close"]),
                    "GrossReturn_pct": stock_return * 100,
                })
        if len(stock_returns) < TOP10:
            raise RuntimeError(f"Missing entry/exit price(s) for {signal}: {entry} to {exit_day}")

        gross = sum(stock_returns) / TOP10
        net = gross - ROUND_TRIP_COST_PCT / 100
        spy0 = get_from_map(entry_map, "SPY")
        spy1 = get_from_map(exit_map, "SPY")
        if not spy0 or not spy1:
            raise RuntimeError("Missing SPY benchmark price")
        spy_return = float(spy1["close"]) / float(spy0["close"]) - 1
        equity *= 1 + net
        spy_equity *= 1 + spy_return
        rows.append({
            "SignalDate": signal,
            "EntryDate": entry,
            "ExitDate": exit_day,
            "Execution": "NEXT_SESSION_CLOSE",
            "RebalanceMonths": rebalance_months,
            "Top10": ",".join(pick.ticker for pick in picks),
            "GrossReturn_pct": gross * 100,
            "Cost_pct": ROUND_TRIP_COST_PCT,
            "NetReturn_pct": net * 100,
            "SPYReturn_pct": spy_return * 100,
            "NetEdgeVsSPY_pct": (net - spy_return) * 100,
            "PortfolioIndex": equity * 100,
            "SPYIndex": spy_equity * 100,
        })
        logging.info("Signal %s, trade %s to %s: %.2f%% net, SPY %.2f%%", signal, entry, exit_day, net * 100, spy_return * 100)

    result = pd.DataFrame(rows)
    result.to_csv("Momentum_backtest_results.csv", index=False)
    pd.DataFrame(position_rows).to_csv("Momentum_backtest_positions.csv", index=False)
    summary = result.groupby("RebalanceMonths").agg(
        Periods=("SignalDate", "count"),
        AvgNetReturn_pct=("NetReturn_pct", "mean"),
        TotalReturn_pct=("PortfolioIndex", lambda values: float(values.iloc[-1] - 100)),
        SPYTotalReturn_pct=("SPYIndex", lambda values: float(values.iloc[-1] - 100)),
    ).reset_index()
    summary["TotalEdgeVsSPY_pct"] = summary["TotalReturn_pct"] - summary["SPYTotalReturn_pct"]
    summary["WinningPeriods"] = int((result["NetReturn_pct"] > 0).sum())
    summary["LosingPeriods"] = int((result["NetReturn_pct"] <= 0).sum())
    summary["PeriodHitRate_pct"] = float((result["NetReturn_pct"] > 0).mean() * 100)
    summary["BestPeriod_pct"] = float(result["NetReturn_pct"].max())
    summary["WorstPeriod_pct"] = float(result["NetReturn_pct"].min())
    summary["RebalancePointMaxDrawdown_pct"] = rebalance_point_max_drawdown(result["PortfolioIndex"])
    summary["Execution"] = "SIGNAL_CLOSE_ENTRY_NEXT_SESSION_CLOSE"
    summary["Universe"] = "CURRENT_TEMPLATE_SURVIVORSHIP_BIAS"
    summary.to_csv("Momentum_backtest_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=(datetime.now(timezone.utc).date() - timedelta(days=365)).isoformat())
    parser.add_argument("--end", default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat())
    parser.add_argument("--rebalance-months", type=int, choices=(1, 2, 3), required=True)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run(arguments.start, arguments.end, arguments.rebalance_months)
