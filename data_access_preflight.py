#!/usr/bin/env python3
"""Fail fast when historical whole-market data cannot support validation.

A model must not be judged from a partial universe.  This small check runs
before the multi-hour point-in-time backtest and verifies that the configured
Massive/Polygon key can retrieve the first required complete U.S. market day.
It performs no trading and writes no portfolio data.
"""
from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

import requests

from backtest_momentum_v3 import fetch_spy_trading_calendar
from momentum_master_v3 import PolygonClient

API_BASE = "https://api.polygon.io"
MIN_EXPECTED_TICKERS = 1_000


def first_trading_day_on_or_after(client: PolygonClient, value: date) -> date:
    """Use observed SPY sessions, including exchange holidays and closures."""
    sessions = fetch_spy_trading_calendar(
        client, value.isoformat(), (value + timedelta(days=14)).isoformat()
    )
    return date.fromisoformat(sessions[0])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify access to the historical whole-market data required for validation."
    )
    parser.add_argument(
        "--start",
        required=True,
        help="First validation date, YYYY-MM-DD. The first SPY trading session is checked.",
    )
    args = parser.parse_args()

    api_key = os.getenv("POLYGON_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "DATA_ACCESS_BLOCKED: POLYGON_API_KEY is missing; no validation was started."
        )

    try:
        start_date = date.fromisoformat(args.start)
    except ValueError as exc:
        raise RuntimeError(f"Invalid validation start date: {args.start!r}") from exc

    requested_date = first_trading_day_on_or_after(PolygonClient(api_key), start_date)

    url = (
        f"{API_BASE}/v2/aggs/grouped/locale/us/market/stocks/"
        f"{requested_date.isoformat()}"
    )
    response = requests.get(
        url,
        params={"apiKey": api_key, "adjusted": "true"},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(
            "DATA_ACCESS_BLOCKED: "
            f"HTTP {response.status_code} for required grouped U.S. market data on "
            f"{requested_date.isoformat()}. The point-in-time validation was not run. "
            "A complete historical whole-market response is required; retrying or "
            "substituting a partial ticker list would make the result unreliable."
        )

    payload = response.json()
    rows = payload.get("results", [])
    if len(rows) < MIN_EXPECTED_TICKERS:
        raise RuntimeError(
            "DATA_ACCESS_BLOCKED: grouped U.S. market response is incomplete "
            f"({len(rows)} rows on {requested_date.isoformat()}; expected at least "
            f"{MIN_EXPECTED_TICKERS}). The point-in-time validation was not run."
        )
    print(
        "Historical whole-market data access verified: "
        f"{requested_date.isoformat()} ({len(rows)} securities)."
    )


if __name__ == "__main__":
    main()
