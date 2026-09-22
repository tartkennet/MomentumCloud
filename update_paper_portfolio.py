#!/usr/bin/env python3
"""Refresh only the user's paper portfolio from verified individual daily closes.

This is a narrow fallback for paper tracking when a provider plan does not expose
the full US grouped-market file. It never reranks candidates, changes the
production model, or sends an order.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from momentum_master_v3 import PolygonClient, normalize_ticker
from momentum_production import PAPER_PORTFOLIO_FILE, _paper_portfolio, _write_json

DASHBOARD_FILE = Path("public/data/dashboard.json")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_latest_paper_closes(
    client: PolygonClient,
    tickers: list[str],
    today=None,
    max_lookback_days: int = 7,
) -> tuple[str, dict]:
    """Return a complete, single-session close map for paper positions and SPY."""
    base_date = today or datetime.now(timezone.utc).date()
    normalized = list(dict.fromkeys(normalize_ticker(ticker) for ticker in tickers))
    for days_back in range(max_lookback_days + 1):
        date_str = (base_date - timedelta(days=days_back)).isoformat()
        try:
            close_map = {
                ticker: client.fetch_daily_open_close(ticker, date_str)
                for ticker in normalized
            }
            return date_str, close_map
        except Exception as exc:
            logging.info("Paper-close date %s unavailable: %s", date_str, exc)
    raise RuntimeError("Could not find a complete recent paper-portfolio close")


def refresh_payload(
    payload: dict,
    client: PolygonClient,
    paper_file: Path = PAPER_PORTFOLIO_FILE,
    today=None,
) -> dict:
    """Update only paper_portfolio in an otherwise already-validated snapshot."""
    seed = _read_json(paper_file)
    positions = seed.get("positions", [])
    if seed.get("status") != "ACTIVE" or not positions:
        raise RuntimeError("Paper portfolio is not active")

    tickers = [normalize_ticker(item["ticker"]) for item in positions] + ["SPY"]
    market_date, close_map = fetch_latest_paper_closes(client, tickers, today=today)

    try:
        fx = float(client.fetch_fx_close(market_date))
        fx_source = "verified USD/SEK close"
    except Exception as exc:
        previous_fx = payload.get("system", {}).get("usdsek") or seed.get("entry_fx")
        if previous_fx is None:
            raise RuntimeError("No verified USD/SEK close or prior FX rate is available") from exc
        fx = float(previous_fx)
        fx_source = "last verified USD/SEK rate; daily return is price-only in SEK"

    paper = _paper_portfolio(close_map, market_date, fx, paper_file)
    paper["pricing_source"] = "Massive individual daily open/close endpoint"
    paper["fx_source"] = fx_source
    if fx_source != "verified USD/SEK close":
        paper["note"] = (
            "Paper tracking only. No orders are sent. Equity prices use verified "
            "daily closes; SEK values use the last verified USD/SEK rate and "
            "exclude fees and taxes."
        )

    updated = dict(payload)
    updated["paper_portfolio"] = paper
    updated["generated_at"] = datetime.now(timezone.utc).isoformat()
    updated.setdefault("system", {})["paper_portfolio_data_status"] = "CONNECTED"
    updated["system"]["paper_portfolio_market_date"] = market_date
    updated["system"]["paper_portfolio_fx_source"] = fx_source
    return updated


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    api_key = os.getenv("POLYGON_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY is required")

    payload = _read_json(DASHBOARD_FILE)
    refreshed = refresh_payload(payload, PolygonClient(api_key))
    _write_json(DASHBOARD_FILE, refreshed)
    paper = refreshed["paper_portfolio"]
    logging.info(
        "Paper portfolio refreshed: %s, %d positions, return=%s%%",
        paper["market_date"],
        paper["position_count"],
        paper.get("portfolio_return_pct"),
    )


if __name__ == "__main__":
    main()
