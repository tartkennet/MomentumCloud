#!/usr/bin/env python3
"""Point-in-time Momentum v3 backtest. Does not alter the daily BuyNow run."""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from momentum_master_v3 import (
    INPUT_TEMPLATE,
    PolygonClient,
    build_metrics,
    alt_ticker,
    get_from_map,
    normalize_ticker,
    read_universe,
    slim_grouped_map,
)

CACHE_FILE = ".momentum_backtest_cache.json"
DEFAULT_TOP_N = 10
ROUND_TRIP_COST_PCT = 0.30
BACKTEST_CACHE_VERSION = 2


def load_backtest_cache(path):
    """Load only caches whose split-adjustment basis is known."""
    cache_path = Path(path)
    if not cache_path.exists():
        return {}, None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        sessions = payload.get("sessions")
        adjusted_through = payload.get("adjusted_through")
        if (
            payload.get("version") != BACKTEST_CACHE_VERSION
            or not isinstance(sessions, dict)
            or not adjusted_through
        ):
            raise ValueError("legacy cache has an unknown split-adjustment basis")
        return sessions, str(adjusted_through)
    except Exception as exc:
        logging.warning("Discarding unsafe backtest cache: %s", exc)
        return {}, None


def save_backtest_cache(path, sessions, adjusted_through):
    payload = {
        "version": BACKTEST_CACHE_VERSION,
        "adjusted_through": str(adjusted_through),
        "sessions": sessions,
    }
    Path(path).write_text(
        json.dumps(payload, separators=(",", ":")),
        encoding="utf-8",
    )


def adjust_cached_history_for_splits(
    cache,
    split_events,
    adjusted_through,
    target_basis_date,
):
    """Move older cached OHLCV rows onto the latest known split basis.

    Polygon's grouped endpoint is split-adjusted when fetched. A persistent
    cache can nevertheless mix rows fetched before and after a later split.
    The cache records the date through which its basis is known; only newer
    split events are applied, making this migration idempotent.
    """
    if not cache or not adjusted_through:
        return 0

    applied = 0
    for event in sorted(split_events, key=lambda item: str(item.get("execution_date", ""))):
        event_day = str(event.get("execution_date", ""))
        if not (str(adjusted_through) < event_day <= str(target_basis_date)):
            continue
        split_from = float(event.get("split_from", 0) or 0)
        split_to = float(event.get("split_to", 0) or 0)
        ticker = normalize_ticker(str(event.get("ticker", "")).upper().strip())
        if not ticker or split_from <= 0 or split_to <= 0:
            continue

        price_factor = split_from / split_to
        volume_factor = split_to / split_from
        touched = 0
        for session_day, day_map in cache.items():
            if session_day >= event_day:
                continue
            row = get_from_map(day_map, ticker)
            if not row:
                continue
            for field in ("open", "high", "low", "close"):
                if field in row and row[field] is not None:
                    row[field] = float(row[field]) * price_factor
            if "volume" in row and row["volume"] is not None:
                row["volume"] = float(row["volume"]) * volume_factor
            touched += 1
        if touched:
            logging.info(
                "Adjusted %d cached %s rows for split %s:%s on %s",
                touched,
                ticker,
                split_from,
                split_to,
                event_day,
            )
            applied += 1
    return applied


# Verified cash corporate actions needed for point-in-time execution.
# FRGE: Schwab completed the all-cash acquisition on 2026-03-02 and paid
# $45.00 per share; the stock therefore has no later exchange print.
# Sources:
# https://pressroom.aboutschwab.com/press-releases/press-release/2026/Charles-Schwab-Completes-Acquisition-of-Forge-Global/default.aspx
# https://www.sec.gov/Archives/edgar/data/1827821/000114036125044598/ny20058741x1_prem14a.htm
CASH_CORPORATE_ACTIONS = {
    "FRGE": {
        "effective_date": "2026-03-02",
        "cash_per_share": 45.0,
        "reason": "CASH_MERGER",
        "execution": "cash-settlement",
    },
}


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
    """Use signal close, then trade in the next session to prevent look-ahead."""
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


def research_exit(
    cache,
    trading_day_strings,
    ticker,
    entry,
    planned_exit,
    exit_rule,
    stop_loss_pct,
    entry_execution="next-close",
    split_events=None,
    entry_reference_price=None,
):
    """Evaluate an exit at each close and execute on the next session."""
    if exit_rule == "rebalance":
        return planned_exit, "REBALANCE"
    sessions = [day for day in trading_day_strings if entry <= day <= planned_exit]
    if len(sessions) < 2:
        return planned_exit, "REBALANCE"
    entry_row = get_from_map(cache[entry], ticker)
    if not entry_row:
        return planned_exit, "REBALANCE"
    entry_price = execution_price(
        entry_row,
        entry_execution,
        split_events,
        entry,
        entry_reference_price,
    )
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
    period_key = "SignalDate" if "SignalDate" in positions.columns else "EntryDate"
    for (_, _), group in positions.groupby([period_key, "PlannedExitDate"], sort=True):
        entry = str(group.iloc[0].get("PlannedEntryDate", group.iloc[0]["EntryDate"]))
        planned_exit = str(group.iloc[0]["PlannedExitDate"])
        final_exit = max(str(value) for value in group["ExitDate"])
        period_end = max(planned_exit, final_exit)
        period_days = [day for day in trading_day_strings if entry <= day <= period_end]
        last_value = period_start_value
        last_prices = {}
        for day in period_days:
            returns = []
            for _, position in group.iterrows():
                ticker = str(position["Ticker"])
                actual_entry = str(position["EntryDate"])
                if day < actual_entry:
                    returns.append(0.0)
                    continue
                if day >= str(position["ExitDate"]):
                    price = float(position["ExitPrice_USD"])
                else:
                    row = get_from_map(cache.get(day, {}), ticker)
                    if row:
                        last_prices[ticker] = float(row["close"])
                    price = last_prices.get(ticker, float(position["EntryPrice_USD"]))
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


def build_legacy_v1_metrics(tickers, latest_map, recent253):
    """Reproduce the verified 2025 v1 ranking without newer v3 filters.

    The original workbook ranked names by the arithmetic mean of the 1, 3,
    6 and 12 month returns. Its BuyNow code required price above SMA200 and
    all four returns to be positive.
    """
    metrics = []
    for ticker in tickers:
        latest = get_from_map(latest_map, ticker)
        if not latest:
            continue
        price = float(latest["close"])
        closes = []
        for _, grouped in recent253:
            row = get_from_map(grouped, ticker)
            if not row:
                break
            closes.append(float(row["close"]))
        if len(closes) < 253:
            continue
        sma200 = sum(closes[:200]) / 200.0
        returns = [(price / closes[index] - 1.0) * 100.0 for index in (21, 63, 126, 252)]
        if price <= sma200 or not all(value > 0 for value in returns):
            continue
        metrics.append(SimpleNamespace(
            ticker=ticker,
            price_usd=price,
            total_score=sum(returns) / 4.0,
        ))
    return metrics


def build_prior_2_12_metrics(tickers, latest_map, recent253, selection_model):
    """Build locked long-only 12-2 research signals.

    classic-12-2 ranks the prior month 2 through 12 return, matching the
    standard momentum formation window without using the most recent month.
    v4-balanced keeps that signal dominant, then rewards 6-2 confirmation,
    lower formation-window volatility and less extension above SMA50.
    """
    if selection_model not in {"classic-12-2", "v4-balanced"}:
        raise ValueError("selection_model must be classic-12-2 or v4-balanced")

    records = []
    for ticker in tickers:
        latest = get_from_map(latest_map, ticker)
        if not latest:
            continue
        price = float(latest["close"])
        closes = []
        dollar_values = []
        for index, (_, grouped) in enumerate(recent253):
            row = get_from_map(grouped, ticker)
            if not row:
                break
            close = float(row["close"])
            closes.append(close)
            if index < 20 and row.get("volume") is not None:
                dollar_values.append(close * float(row["volume"]))
        if len(closes) < 253 or len(dollar_values) < 10:
            continue

        adv20 = sum(dollar_values) / len(dollar_values)
        sma50 = sum(closes[:50]) / 50.0
        sma200 = sum(closes[:200]) / 200.0
        sma200_1m_ago = sum(closes[21:221]) / 200.0
        mom12_2 = (closes[21] / closes[252] - 1.0) * 100.0
        mom6_2 = (closes[21] / closes[126] - 1.0) * 100.0
        formation = list(reversed(closes[21:127]))
        daily_returns = [
            later / earlier - 1.0
            for earlier, later in zip(formation, formation[1:])
            if earlier > 0 and later > 0
        ]
        if len(daily_returns) < 80:
            continue
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((value - mean_return) ** 2 for value in daily_returns) / (
            len(daily_returns) - 1
        )
        annualized_vol = math.sqrt(max(variance, 0.0)) * math.sqrt(252.0) * 100.0
        dist_sma50 = (price / sma50 - 1.0) * 100.0

        if selection_model == "classic-12-2":
            if (
                price < 5.0
                or adv20 < 20_000_000.0
                or price <= sma200
                or mom12_2 <= 0.0
            ):
                continue
        else:
            if (
                price < 10.0
                or adv20 < 50_000_000.0
                or price <= sma50
                or price <= sma200
                or sma200 <= sma200_1m_ago
                or mom12_2 <= 0.0
                or mom6_2 <= 0.0
            ):
                continue

        records.append({
            "ticker": ticker,
            "price_usd": price,
            "mom12_2": mom12_2,
            "mom6_2": mom6_2,
            "annualized_vol": annualized_vol,
            "dist_sma50": dist_sma50,
        })

    if selection_model == "classic-12-2":
        return [
            SimpleNamespace(
                ticker=row["ticker"],
                price_usd=row["price_usd"],
                total_score=row["mom12_2"],
            )
            for row in records
        ]
    if not records:
        return []

    frame = pd.DataFrame(records)
    frame["rank_12_2"] = frame["mom12_2"].rank(method="average", pct=True)
    frame["rank_6_2"] = frame["mom6_2"].rank(method="average", pct=True)
    frame["rank_low_vol"] = frame["annualized_vol"].rank(
        method="average", ascending=False, pct=True
    )
    frame["rank_low_extension"] = frame["dist_sma50"].rank(
        method="average", ascending=False, pct=True
    )
    frame["total_score"] = 100.0 * (
        0.55 * frame["rank_12_2"]
        + 0.20 * frame["rank_6_2"]
        + 0.15 * frame["rank_low_vol"]
        + 0.10 * frame["rank_low_extension"]
    )
    return [
        SimpleNamespace(
            ticker=str(row.ticker),
            price_usd=float(row.price_usd),
            total_score=float(row.total_score),
        )
        for row in frame.itertuples(index=False)
    ]


def choose_top(client, cache, tickers, asof, top_n=DEFAULT_TOP_N, selection_model="v3"):
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    if selection_model not in {"v3", "legacy-v1", "classic-12-2", "v4-balanced"}:
        raise ValueError(
            "selection_model must be v3, legacy-v1, classic-12-2 or v4-balanced"
        )
    signal_map = cache.get(asof)
    if signal_map is None:
        signal_map = slim_grouped_map(client.fetch_grouped_stocks(asof), tickers)
        cache[asof] = signal_map
    history = session_window(client, cache, tickers, asof)
    if selection_model == "legacy-v1":
        metrics = build_legacy_v1_metrics(tickers, signal_map, history)
    elif selection_model in {"classic-12-2", "v4-balanced"}:
        metrics = build_prior_2_12_metrics(
            tickers, signal_map, history, selection_model
        )
    else:
        metrics, _, _ = build_metrics(tickers, signal_map, history)
    return sorted(metrics, key=lambda item: item.total_score, reverse=True)[:top_n]


def choose_top10(client, cache, tickers, asof):
    """Backward-compatible helper for the original ten-position research."""
    return choose_top(client, cache, tickers, asof, DEFAULT_TOP_N)


def execution_price(
    row,
    execution,
    split_events=None,
    execution_date=None,
    reference_price=None,
):
    """Return an executable price on the same split basis as the session close.

    Polygon's grouped feed is adjusted, but an occasional split-session open can
    arrive on the pre-split basis while that session's close is post-split. For
    next-open simulation we normalize only a large mismatch that resolves to the
    same basis as the close. Verified split events are preferred, with a narrow
    fallback for common split ratios when the provider omits the event.
    """
    field = "open" if execution == "next-open" else "close"
    price = float(row.get(field, row["close"]))
    if execution != "next-open":
        return price

    close = float(row.get("close", price))
    basis_price = float(reference_price) if reference_price is not None else close
    if price <= 0 or basis_price <= 0:
        return price

    candidates = [price]
    for event in split_events or []:
        if str(event.get("execution_date", "")) != str(execution_date):
            continue
        split_from = float(event.get("split_from", 0) or 0)
        split_to = float(event.get("split_to", 0) or 0)
        if split_from > 0 and split_to > 0:
            ratio = split_to / split_from
            candidates.extend([price * ratio, price / ratio])

    # Provider split records can lag or omit an event. Only accept a familiar
    # split factor when it changes a 50%+ mismatch into a price within 10% of
    # that day's close, so normal opening gaps are never rewritten.
    for ratio in (2.0, 3.0, 4.0, 5.0, 10.0):
        candidates.extend([price * ratio, price / ratio])

    normalized = min(candidates, key=lambda value: abs(math.log(value / basis_price)))
    raw_gap = abs(math.log(price / basis_price))
    normalized_gap = abs(math.log(normalized / basis_price))
    if (
        normalized != price
        and raw_gap >= math.log(1.5)
        and normalized_gap <= math.log(1.1)
    ):
        logging.warning(
            "Normalized split-like open %.4f to %.4f on %s",
            price,
            normalized,
            execution_date,
        )
        return normalized
    return price


def first_tradable_row(cache, trading_day_strings, ticker, target_day, latest_day=None):
    """Find the first actual ticker print on or after an intended execution day.

    A market can be open while an individual security is halted or has no daily
    aggregate. An order cannot fill until that security trades again, so a
    missing row delays execution instead of removing the position or aborting
    the whole portfolio simulation.
    """
    for day in trading_day_strings:
        if day < target_day:
            continue
        if latest_day is not None and day > latest_day:
            break
        row = get_from_map(cache.get(day, {}), ticker)
        if row:
            return day, row
    return None, None


def resolve_exit_execution(
    cache,
    trading_day_strings,
    ticker,
    target_day,
    entry_day,
    latest_day,
):
    """Resolve a market exit or a verified cash corporate action.

    A tradable exchange print on or after the target day takes precedence up to
    the corporate-action effective date. If the security never trades again,
    the position is settled at the verified cash consideration.
    """
    action = CASH_CORPORATE_ACTIONS.get(ticker)
    eligible_action = None
    search_latest = latest_day
    if action:
        action_day = str(action["effective_date"])
        if entry_day < action_day <= latest_day:
            eligible_action = action
            search_latest = min(latest_day, action_day)

    resolved_day, row = first_tradable_row(
        cache,
        trading_day_strings,
        ticker,
        target_day,
        search_latest,
    )
    if row:
        return resolved_day, row, None
    if eligible_action:
        cash_price = float(eligible_action["cash_per_share"])
        return (
            str(eligible_action["effective_date"]),
            {"open": cash_price, "close": cash_price},
            eligible_action,
        )
    return None, None, None


def run(
    start,
    end,
    rebalance_months,
    stop_loss_pct=None,
    exit_rule=None,
    exit_execution="next-close",
    top_n=DEFAULT_TOP_N,
    entry_execution="next-close",
    rebalance_exit_execution="next-close",
    selection_model="v3",
):
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("Missing POLYGON_API_KEY")
    client = PolygonClient(api_key)
    tickers = read_universe(INPUT_TEMPLATE)
    history_tickers = list(dict.fromkeys(tickers + ["SPY"]))
    cache, adjusted_through = load_backtest_cache(CACHE_FILE)
    start_day = datetime.fromisoformat(start).date()
    end_day = datetime.fromisoformat(end).date()
    if start_day >= end_day:
        raise ValueError("start must be earlier than end")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    if selection_model not in {"v3", "legacy-v1", "classic-12-2", "v4-balanced"}:
        raise ValueError(
            "selection_model must be v3, legacy-v1, classic-12-2 or v4-balanced"
        )

    needed_sessions = 253 + int((end_day - start_day).days * 5 / 7) + 10
    exit_rule = exit_rule or ("stop" if stop_loss_pct is not None else "rebalance")
    if exit_rule == "stop" and stop_loss_pct is None:
        raise ValueError("stop exit rule requires --stop-loss-pct")
    require_ohlc = "next-open" in (
        exit_execution,
        entry_execution,
        rebalance_exit_execution,
    )
    cache_basis_day = datetime.now(timezone.utc).date().isoformat()
    if cache and adjusted_through < cache_basis_day:
        new_splits = client.fetch_recent_splits(adjusted_through, cache_basis_day)
        adjust_cached_history_for_splits(
            cache,
            new_splits,
            adjusted_through,
            cache_basis_day,
        )

    all_days = trading_dates(client, end_day, needed_sessions, cache=cache, require_ohlc=require_ohlc)
    for date_string, grouped in all_days:
        cache[date_string] = slim_grouped_map(grouped, history_tickers)
    save_backtest_cache(CACHE_FILE, cache, cache_basis_day)

    trading_day_strings = [date for date, _ in all_days]
    split_events_by_ticker = {}
    for event in client.fetch_recent_splits(start, end):
        ticker = str(event.get("ticker", "")).upper().strip()
        if ticker:
            split_events_by_ticker.setdefault(ticker, []).append(event)
    signals = calendar_rebalance_signals(trading_day_strings, start, end, rebalance_months)
    periods = execution_periods(trading_day_strings, signals, end)
    if not periods:
        raise RuntimeError("No executable rebalance periods in requested range")

    rows, position_rows, equity, spy_equity = [], [], 1.0, 1.0
    for signal, entry, exit_day in periods:
        picks = choose_top(client, cache, tickers, signal, top_n, selection_model)
        if len(picks) < top_n:
            raise RuntimeError(f"Only {len(picks)} qualified names on {signal}")
        entry_map = cache[entry]
        exit_map = cache[exit_day]
        stock_returns = []
        missing_executions = []
        for rank, pick in enumerate(picks, start=1):
            actual_entry, entry_row = first_tradable_row(
                cache, trading_day_strings, pick.ticker, entry, exit_day
            )
            if not entry_row or actual_entry >= exit_day:
                missing_executions.append(f"{pick.ticker}(entry from {entry})")
                continue
            actual_exit, exit_reason = research_exit(
                cache,
                trading_day_strings,
                pick.ticker,
                actual_entry,
                exit_day,
                exit_rule,
                stop_loss_pct,
                entry_execution,
                split_events_by_ticker.get(pick.ticker, []),
                pick.price_usd,
            )
            resolved_exit, exit_row, corporate_action = resolve_exit_execution(
                cache,
                trading_day_strings,
                pick.ticker,
                actual_exit,
                actual_entry,
                trading_day_strings[-1],
            )
            if not exit_row or resolved_exit <= actual_entry:
                missing_executions.append(f"{pick.ticker}(exit from {actual_exit})")
                continue
            if corporate_action:
                exit_reason = str(corporate_action["reason"])
                applied_exit_execution = str(corporate_action["execution"])
            else:
                applied_exit_execution = (
                    exit_execution if exit_reason != "REBALANCE" else rebalance_exit_execution
                )
            split_events = split_events_by_ticker.get(pick.ticker, [])
            entry_price = execution_price(
                entry_row,
                entry_execution,
                split_events,
                actual_entry,
                pick.price_usd,
            )
            prior_exit_reference = None
            exit_index = trading_day_strings.index(resolved_exit)
            if exit_index > 0:
                prior_exit_row = get_from_map(
                    cache[trading_day_strings[exit_index - 1]], pick.ticker
                )
                if prior_exit_row:
                    prior_exit_reference = float(prior_exit_row["close"])
            exit_price = (
                float(exit_row["close"])
                if corporate_action
                else execution_price(
                    exit_row,
                    applied_exit_execution,
                    split_events,
                    resolved_exit,
                    prior_exit_reference,
                )
            )
            stock_return = exit_price / entry_price - 1
            stock_returns.append(stock_return)
            entry_delay = trading_day_strings.index(actual_entry) - trading_day_strings.index(entry)
            exit_delay = (
                0
                if corporate_action
                else trading_day_strings.index(resolved_exit) - trading_day_strings.index(actual_exit)
            )
            if entry_delay or exit_delay:
                logging.warning(
                    "%s execution delayed: entry %s->%s, exit %s->%s",
                    pick.ticker,
                    entry,
                    actual_entry,
                    actual_exit,
                    resolved_exit,
                )
            position_rows.append({
                "SignalDate": signal,
                "PlannedEntryDate": entry,
                "EntryDate": actual_entry,
                "ExitDate": resolved_exit,
                "PlannedExitDate": exit_day,
                "ExitReason": exit_reason,
                "CorporateAction": (
                    str(corporate_action["reason"]) if corporate_action else ""
                ),
                "EntryExecution": entry_execution,
                "ExitExecution": applied_exit_execution,
                "EntryDelaySessions": entry_delay,
                "ExitDelaySessions": exit_delay,
                "StopLoss_pct": stop_loss_pct,
                "RebalanceMonths": rebalance_months,
                "TopN": top_n,
                "SelectionModel": selection_model,
                "Rank": rank,
                "Ticker": pick.ticker,
                "SignalPrice_USD": pick.price_usd,
                "EntryPrice_USD": entry_price,
                "ExitPrice_USD": exit_price,
                "GrossReturn_pct": stock_return * 100,
            })
        if len(stock_returns) < top_n:
            details = ", ".join(missing_executions) or "unknown ticker"
            raise RuntimeError(
                f"No executable price through available history for {signal}: {details}"
            )

        gross = sum(stock_returns) / top_n
        net = gross - ROUND_TRIP_COST_PCT / 100
        spy0 = get_from_map(entry_map, "SPY")
        spy1 = get_from_map(exit_map, "SPY")
        if not spy0 or not spy1:
            raise RuntimeError("Missing SPY benchmark price")
        spy_return = (
            execution_price(spy1, rebalance_exit_execution)
            / execution_price(spy0, entry_execution)
            - 1
        )
        equity *= 1 + net
        spy_equity *= 1 + spy_return
        rows.append({
            "SignalDate": signal,
            "EntryDate": entry,
            "ExitDate": exit_day,
            "Execution": f"ENTRY_{entry_execution.upper()}_REBALANCE_{rebalance_exit_execution.upper()}",
            "RebalanceMonths": rebalance_months,
            "TopN": top_n,
            "SelectionModel": selection_model,
            "ExitRule": exit_rule,
            "EntryExecution": entry_execution,
            "ExitExecution": exit_execution,
            "RebalanceExitExecution": rebalance_exit_execution,
            "StopLoss_pct": stop_loss_pct,
            "TopTickers": ",".join(pick.ticker for pick in picks),
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
    summary["TopN"] = top_n
    summary["SelectionModel"] = selection_model
    summary["EntryExecution"] = entry_execution
    summary["ExitExecution"] = exit_execution
    summary["RebalanceExitExecution"] = rebalance_exit_execution
    summary["StopLoss_pct"] = stop_loss_pct
    summary["EarlyExitPositions"] = int((pd.DataFrame(position_rows)["ExitReason"] != "REBALANCE").sum())
    summary["Execution"] = (
        f"SIGNAL_CLOSE_ENTRY_{entry_execution.upper()}_REBALANCE_{rebalance_exit_execution.upper()}"
    )
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
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--entry-execution", choices=("next-close", "next-open"), default="next-close")
    parser.add_argument("--rebalance-exit-execution", choices=("next-close", "next-open"), default="next-close")
    parser.add_argument(
        "--selection-model",
        choices=("v3", "legacy-v1", "classic-12-2", "v4-balanced"),
        default="v3",
    )
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run(
        arguments.start,
        arguments.end,
        arguments.rebalance_months,
        arguments.stop_loss_pct,
        arguments.exit_rule,
        arguments.exit_execution,
        arguments.top_n,
        arguments.entry_execution,
        arguments.rebalance_exit_execution,
        arguments.selection_model,
    )
