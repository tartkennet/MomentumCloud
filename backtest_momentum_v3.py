#!/usr/bin/env python3
"""Point-in-time Momentum v3 backtest. Does not alter the daily BuyNow run."""
from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
from momentum_master_v3 import (
    PolygonClient, build_metrics, get_from_map, read_universe, slim_grouped_map,
    load_history_cache, save_history_cache, INPUT_TEMPLATE,
)

CACHE_FILE = ".momentum_backtest_cache.json"
TOP10 = 10
ROUND_TRIP_COST_PCT = 0.30  # 0.15% entry + 0.15% exit, conservative all-in assumption

def trading_dates(client, end_date, count):
    dates, day = [], end_date
    while len(dates) < count:
        if day.weekday() < 5:
            grouped = client.fetch_grouped_stocks(day.isoformat())
            if len(grouped) > 1000:
                dates.append((day.isoformat(), grouped))
        day -= timedelta(days=1)
    return list(reversed(dates))

def session_window(client, cache, tickers, asof, needed=253):
    if asof not in cache:
        cache[asof] = slim_grouped_map(client.fetch_grouped_stocks(asof), tickers)
    dates = sorted(d for d in cache if d <= asof)
    # Fetch only missing weekdays within the required calendar window.
    day = datetime.fromisoformat(asof).date()
    while len([d for d in cache if d <= asof]) < needed:
        if day.weekday() < 5:
            ds = day.isoformat()
            if ds not in cache:
                grouped = client.fetch_grouped_stocks(ds)
                if len(grouped) > 1000:
                    cache[ds] = slim_grouped_map(grouped, tickers)
        day -= timedelta(days=1)
    dates = sorted((d for d in cache if d <= asof), reverse=True)[:needed]
    return [(d, cache[d]) for d in dates]

def choose_top10(client, cache, tickers, asof):
    latest = cache.get(asof)
    if latest is None:
        latest = slim_grouped_map(client.fetch_grouped_stocks(asof), tickers)
        cache[asof] = latest
    history = session_window(client, cache, tickers, asof)
    metrics, _, _ = build_metrics(tickers, latest, history)
    ranked = sorted(metrics, key=lambda x: x.total_score, reverse=True)[:TOP10]
    return ranked, latest

def run(start, end, rebalance_months):
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("Missing POLYGON_API_KEY")
    client = PolygonClient(api_key)
    tickers = read_universe(INPUT_TEMPLATE)
    cache = load_history_cache(CACHE_FILE)
    # Build a monthly decision calendar from valid trading sessions. 253 sessions before
    # the first decision are required because the live model uses a 12-month signal.
    all_days = trading_dates(client, end, 253 + 24 * 22)
    decisions = [d for d, _ in all_days if start <= d <= end]
    decisions = decisions[::rebalance_months * 22]
    rows, equity, spy_equity = [], 1.0, 1.0
    for entry, exit_ in zip(decisions, decisions[1:] + [end]):
        picks, entry_map = choose_top10(client, cache, tickers, entry)
        if len(picks) < TOP10:
            raise RuntimeError(f"Only {len(picks)} qualified names on {entry}")
        exit_map = slim_grouped_map(client.fetch_grouped_stocks(exit_), tickers + ["SPY"])
        stock_returns = []
        for pick in picks:
            close_exit = get_from_map(exit_map, pick.ticker)
            if close_exit:
                stock_returns.append(float(close_exit["close"]) / pick.price_usd - 1)
        if len(stock_returns) < TOP10:
            raise RuntimeError(f"Missing exit price(s) for {entry} to {exit_}")
        gross = sum(stock_returns) / TOP10
        net = gross - ROUND_TRIP_COST_PCT / 100
        spy0 = get_from_map(entry_map, "SPY")
        spy1 = get_from_map(exit_map, "SPY")
        if not spy0 or not spy1:
            raise RuntimeError("Missing SPY benchmark price")
        spy_ret = float(spy1["close"]) / float(spy0["close"]) - 1
        equity *= 1 + net
        spy_equity *= 1 + spy_ret
        rows.append({"EntryDate":entry,"ExitDate":exit_,"RebalanceMonths":rebalance_months,
                     "Top10":",".join(p.ticker for p in picks),"GrossReturn_pct":gross*100,
                     "Cost_pct":ROUND_TRIP_COST_PCT,"NetReturn_pct":net*100,
                     "SPYReturn_pct":spy_ret*100,"NetEdgeVsSPY_pct":(net-spy_ret)*100,
                     "PortfolioIndex":equity*100,"SPYIndex":spy_equity*100})
        save_history_cache(CACHE_FILE, [(d, cache[d]) for d in cache])
        logging.info("%s to %s: %.2f%% net, SPY %.2f%%", entry, exit_, net*100, spy_ret*100)
    result = pd.DataFrame(rows)
    result.to_csv("Momentum_backtest_results.csv", index=False)
    summary = result.groupby("RebalanceMonths").agg(
        Periods=("EntryDate","count"), AvgNetReturn_pct=("NetReturn_pct","mean"),
        TotalReturn_pct=("PortfolioIndex", lambda x: float(x.iloc[-1]-100)),
        SPYTotalReturn_pct=("SPYIndex", lambda x: float(x.iloc[-1]-100)),
        AvgEdgeVsSPY_pct=("NetEdgeVsSPY_pct","mean")).reset_index()
    summary.to_csv("Momentum_backtest_summary.csv", index=False)
    print(summary.to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=(datetime.now(timezone.utc).date()-timedelta(days=365)).isoformat())
    parser.add_argument("--end", default=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat())
    parser.add_argument("--rebalance-months", type=int, choices=(1,3), required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run(args.start, args.end, args.rebalance_months)
