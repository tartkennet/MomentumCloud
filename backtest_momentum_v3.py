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


def trading_dates(client, end_date, count, cache=None, require_ohlc=False):
    """Return recent trading sessions, reusing the persistent history cache."""
    cache = cache or {}
    dates, day = [], end_date
    while len(dates) < count:
        if day.weekday() < 5:
            date_string = day.isoformat()
            cached = cache.get(date_string)
            has_ohlc = cached and any("open" in row for row in cached.values())
            if cached is not None and (not require_ohlc or has_ohlc):
                dates.append((date_string, cached))
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


def research_exit(cache, trading_day_strings, ticker, entry, planned_exit, exit_rule, stop_loss_pct):
    """Evaluate an exit at each close and execute on the next session."""
    if exit_rule == "rebalance":
        return planned_exit, "REBALANCE"
    sessions = [day for day in trading_day_strings if entry <= day <= planned_exit]
    if len(sessions) < 2:
        return planned_exit, "REBALANCE"
    entry_row = get_from_map(cache[entry], ticker)
    if not entry_row:
        return planned_exit, "REBALANCE"
    entry_price = float(entry_row["close"])
    for index, signal_day in enumerate(sessions[:-1]):
        row = get_from_map(cache[signal_day], ticker)
        if not row:
            continue
        triggered = False
        reason = "REBALANCE"
        if exit_rule == "stop":
            threshold = -abs(float(stop_loss_pct)) / 100.0
            triggered = float(row["close"]) / entry_price - 1.0 <= threshold
            reason = "STOP_LOSS"
        elif exit_rule == "sma50":
            history_days = sorted((day for day in cache if day <= signal_day), reverse=True)[:50]
            closes = [
                float(value["close"])
                for day in history_days
                for value in [get_from_map(cache[day], ticker)]
                if value
            ]
            triggered = len(closes) == 50 and float(row["close"]) < sum(closes) / 50.0
            reason = "BELOW_SMA50"
        elif exit_rule == "momentum":
            history_days = sorted((day for day in cache if day <= signal_day), reverse=True)[:253]
            history = [(day, cache[day]) for day in history_days]
            passed, _, _ = build_metrics([ticker], cache[signal_day], history)
            triggered = not passed
            reason = "OUT_OF_MOMENTUM"
        if triggered:
            return sessions[index + 1], reason
    return planned_exit, "REBALANCE"


def stop_loss_exit(cache, trading_day_strings, ticker, entry, planned_exit, stop_loss_pct):
    """Backward-compatible stop-loss helper used by unit tests."""
    return research_exit(
        cache, trading_day_strings, ticker, entry, planned_exit, "stop", stop_loss_pct
    ) if stop_loss_pct is not None else (planned_exit, "REBALANCE")


def daily_portfolio_max_drawdown(position_rows, cache, trading_day_strings):
    """Calculate drawdown from daily closes, holding exited positions as cash."""
    if not position_rows:
        return 0.0
    positions = pd.DataFrame(position_rows)
    index_values = []
    period_start_value = 100.0
    for (_, _), group in positions.groupby(["EntryDate", "PlannedExitDate"], sort=True):
        entry = str(group.iloc[0]["EntryDate"])
        planned_exit = str(group.iloc[0]["PlannedExitDate"])
        period_days = [day for day in trading_day_strings if entry <= day <= planned_exit]
        last_value = period_start_value
        for day in period_days:
            returns = []
            for _, position in group.iterrows():
                if day >= str(position["ExitDate"]):
                    price = float(position["ExitPrice_USD"])
                else:
                    row = get_from_map(cache[day], str(position["Ticker"]))
                    price = float(row["close"]) if row else float(position["EntryPrice_USD"])
                returns.append(price / float(position["EntryPrice_USD"]) - 1.0)
            last_value = period_start_value * (
                1.0 + sum(returns) / len(returns) - ROUND_TRIP_COST_PCT / 100.0
            )
            index_values.append(last_value)
        period_start_value = last_value
    return rebalance_point_max_drawdown(index_values)


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


def run(start, end, rebalance_months, stop_loss_pct=None, exit_rule=None, exit_execution="next-close"):
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
    exit_rule = exit_rule or ("stop" if stop_loss_pct is not None else "rebalance")
    if exit_rule == "stop" and stop_loss_pct is None:
        raise ValueError("stop exit rule requires --stop-loss-pct")
    require_ohlc = exit_execution == "next-open"
    all_days = trading_dates(client, end_day, needed_sessions, cache=cache, require_ohlc=require_ohlc)
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
            actual_exit, exit_reason = research_exit(
                cache, trading_day_strings, pick.ticker, entry, exit_day, exit_rule, stop_loss_pct
            )
            actual_exit_map = cache[actual_exit]
            exit_row = get_from_map(actual_exit_map, pick.ticker)
            if entry_row and exit_row:
                exit_price_field = "open" if exit_reason != "REBALANCE" and exit_execution == "next-open" else "close"
                exit_price = float(exit_row.get(exit_price_field, exit_row["close"]))
                stock_return = exit_price / float(entry_row["close"]) - 1
                stock_returns.append(stock_return)
                position_rows.append({
                    "SignalDate": signal,
                    "EntryDate": entry,
                    "ExitDate": actual_exit,
                    "PlannedExitDate": exit_day,
                    "ExitReason": exit_reason,
                    "ExitExecution": exit_execution,
                    "StopLoss_pct": stop_loss_pct,
                    "RebalanceMonths": rebalance_months,
                    "Rank": rank,
                    "Ticker": pick.ticker,
                    "SignalPrice_USD": pick.price_usd,
                    "EntryPrice_USD": float(entry_row["close"]),
                    "ExitPrice_USD": exit_price,
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
            "ExitRule": exit_rule,
            "ExitExecution": exit_execution,
            "StopLoss_pct": stop_loss_pct,
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
    summary["DailyMaxDrawdown_pct"] = daily_portfolio_max_drawdown(
        position_rows, cache, trading_day_strings
    )
    summary["ExitRule"] = exit_rule
    summary["ExitExecution"] = exit_execution
    summary["StopLoss_pct"] = stop_loss_pct
    summary["EarlyExitPositions"] = int((pd.DataFrame(position_rows)["ExitReason"] != "REBALANCE").sum())
    summary["Execution"] = "SIGNAL_CLOSE_ENTRY_NEXT_SESSION"
    summary["Universe"] = "CURRENT_TEMPLATE_SURVIVORSHIP_BIAS"
    summary.to_csv("Momentum_backtest_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=(datetime.now(timezone.utc).date() - timedelta(days=365)).isoformat())
    parser.add_argument("--end", default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat())
    parser.add_argument("--rebalance-months", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--stop-loss-pct", type=float)
    parser.add_argument("--exit-rule", choices=("rebalance", "stop", "sma50", "momentum"))
    parser.add_argument("--exit-execution", choices=("next-close", "next-open"), default="next-close")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run(
        arguments.start,
        arguments.end,
        arguments.rebalance_months,
        arguments.stop_loss_pct,
        arguments.exit_rule,
        arguments.exit_execution,
    )
