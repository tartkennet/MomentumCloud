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

API_BASE = "https://api.polygon.io"
MIN_EXPECTED_TICKERS = 1_000
FORMATION_CALENDAR_DAYS = 450


def first_weekday_on_or_after(value: date) -> date:
    while value.weekday() >= 5:
        value += timedelta(days=1)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify access to the historical whole-market data required for validation."
    )
    parser.add_argument(
        "--start",
        required=True,
        help=(
            "First validation date, YYYY-MM-DD. The required formation-history "
            "date is checked before the validation is started."
        ),
    )
    args = parser.parse_args()

    api_key = os.getenv("POLYGON_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "DATA_ACCESS_BLOCKED: POLYGON_API_KEY is missing; no validation was started."
        )

    try:
        validation_start = date.fromisoformat(args.start)
    except ValueError as exc:
        raise RuntimeError(f"Invalid validation start date: {args.start!r}") from exc

    # A 12-2 momentum and SMA200 calculation needs roughly 253 sessions of
    # prior prices.  Checking the formation window, not merely the requested
    # test start, prevents a five-year plan from producing a partial backtest.
    requested_date = first_weekday_on_or_after(
        validation_start - timedelta(days=FORMATION_CALENDAR_DAYS)
    )

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
