#!/usr/bin/env python3
from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

POLYGON_BASE = "https://api.polygon.io"
INPUT_TEMPLATE = "Momentum mall fil.xlsx"
OUTPUT_FILE = "Momentum.xlsx"
UNIVERSE_SHEET = "Universe"
PARAM_SHEET = "Parametrar"
BUYNOW_SHEET = "BuyNow"
DIAGNOSTICS_SHEET = "Diagnostics"

MIN_PRICE = 5.0
MIN_ADTV20 = 20_000_000.0
MIN_TOTAL_SCORE = 15.0
TOP_N = 15
TOP10_N = 10


@dataclass
class StockMetrics:
    ticker: str
    price_usd: float
    avg_dollar_volume20: float
    sma50: float
    sma200: float
    ret1m: float
    ret3m: float
    ret6m: float
    ret12m: float
    accel: float
    total_score: float


class PolygonClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = requests.Session()

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        merged = {"apiKey": self.api_key}
        if params:
            merged.update(params)
        response = self.session.get(f"{POLYGON_BASE}{path}", params=merged, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ERROR":
            raise RuntimeError(f"Polygon API error: {data}")
        return data

    def fetch_grouped_close(self, date_str: str, from_ccy: str, to_ccy: str) -> float:
        pair = f"C:{from_ccy}{to_ccy}"
        data = self._get(
            f"/v2/aggs/ticker/{pair}/range/1/day/{date_str}/{date_str}",
            {"adjusted": "true", "limit": 10},
        )
        results = data.get("results", [])
        if not results:
            raise ValueError(f"No FX result for {pair} on {date_str}")
        return float(results[-1]["c"])

    def fetch_daily_bars(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        data = self._get(
            f"/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}",
            {"adjusted": "true", "sort": "asc", "limit": 5000},
        )
        results = data.get("results", [])
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results).rename(
            columns={"t": "ts", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        )
        df["date"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_convert(None)
        return df[["date", "open", "high", "low", "close", "volume"]].copy()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def read_universe(path: str) -> List[str]:
    df = pd.read_excel(path, sheet_name=UNIVERSE_SHEET)
    if "Ticker" not in df.columns:
        raise ValueError("Universe sheet must contain a 'Ticker' column")
    tickers = df["Ticker"].dropna().astype(str).str.strip().str.upper().replace("", np.nan).dropna().tolist()
    unique = list(dict.fromkeys(tickers))
    if not unique:
        raise ValueError("No tickers found in Universe sheet")
    return unique


def read_portfolio_value_sek(path: str) -> float:
    wb = load_workbook(path, data_only=True)
    ws = wb[PARAM_SHEET]
    value = ws["B1"].value
    if value is None:
        raise ValueError("Parametrar!B1 is empty")
    parsed = float(value)
    if parsed <= 0:
        raise ValueError("Parametrar!B1 must be > 0")
    return parsed


def pick_grouped_date_with_fx(client: PolygonClient, max_lookback_days: int = 7) -> str:
    today_utc = datetime.now(timezone.utc).date()
    for delta in range(1, max_lookback_days + 1):
        candidate = (today_utc - timedelta(days=delta)).isoformat()
        try:
            client.fetch_grouped_close(candidate, "USD", "SEK")
            return candidate
        except Exception:
            continue
    raise RuntimeError(f"Unable to find recent USDSEK FX bar in last {max_lookback_days} days")


def compute_metrics(ticker: str, bars: pd.DataFrame, counters: Dict[str, int]) -> Optional[StockMetrics]:
    if bars.empty:
        return None

    counters["tickers_with_valid_polygon_data"] += 1

    if len(bars) < 253:
        counters["excluded_by_insufficient_history"] += 1
        return None

    closes = bars["close"].astype(float).reset_index(drop=True)
    volumes = bars["volume"].astype(float).reset_index(drop=True)
    if closes.isna().any() or volumes.isna().any():
        counters["excluded_by_insufficient_history"] += 1
        return None

    price = float(closes.iloc[-1])
    if price < MIN_PRICE:
        counters["excluded_by_price_filter"] += 1
        return None

    adv20 = float((closes.iloc[-20:] * volumes.iloc[-20:]).mean())
    if adv20 < MIN_ADTV20:
        counters["excluded_by_liquidity_filter"] += 1
        return None

    sma50 = float(closes.iloc[-50:].mean())
    sma200 = float(closes.iloc[-200:].mean())
    if not (price > sma50 and price > sma200):
        counters["excluded_by_trend_filter"] += 1
        return None

    ret1m = (price / float(closes.iloc[-22]) - 1.0) * 100.0
    ret3m = (price / float(closes.iloc[-64]) - 1.0) * 100.0
    ret6m = (price / float(closes.iloc[-127]) - 1.0) * 100.0
    ret12m = (price / float(closes.iloc[-253]) - 1.0) * 100.0

    if not (ret3m > 0 and ret6m > 0):
        counters["excluded_by_momentum_filter"] += 1
        return None

    accel = ret1m - ret3m
    stock_momentum = 0.40 * ret1m + 0.30 * ret3m + 0.20 * ret6m + 0.10 * ret12m
    total_score = stock_momentum + 0.10 * accel
    if total_score <= MIN_TOTAL_SCORE:
        counters["excluded_by_momentum_filter"] += 1
        return None

    return StockMetrics(
        ticker=ticker,
        price_usd=price,
        avg_dollar_volume20=adv20,
        sma50=sma50,
        sma200=sma200,
        ret1m=ret1m,
        ret3m=ret3m,
        ret6m=ret6m,
        ret12m=ret12m,
        accel=accel,
        total_score=total_score,
    )


def build_buynow_df(metrics: List[StockMetrics], fx: float, portfolio_value_sek: float) -> pd.DataFrame:
    ranked = sorted(metrics, key=lambda x: x.total_score, reverse=True)[:TOP_N]
    rows = []
    position_size_sek = portfolio_value_sek / TOP10_N
    for rank, metric in enumerate(ranked, start=1):
        is_top10 = rank <= TOP10_N
        price_sek = metric.price_usd * fx
        qty = max(1, math.floor(position_size_sek / price_sek)) if is_top10 else ""
        rows.append(
            {
                "Rank": rank,
                "Ticker": metric.ticker,
                "Top10": bool(is_top10),
                "Qty": qty,
                "Price_USD": metric.price_usd,
                "FX": fx,
                "Price_SEK": price_sek,
                "Position_SEK": position_size_sek if is_top10 else "",
                "AvgDollarVolume20": metric.avg_dollar_volume20,
                "SMA50": metric.sma50,
                "SMA200": metric.sma200,
                "Ret1m": metric.ret1m,
                "Ret3m": metric.ret3m,
                "Ret6m": metric.ret6m,
                "Ret12m": metric.ret12m,
                "Accel": metric.accel,
                "TotalScore": metric.total_score,
            }
        )
    return pd.DataFrame(rows)


def autosize_columns(ws) -> None:
    for col_idx, _ in enumerate(ws[1], start=1):
        max_len = 0
        col_letter = get_column_letter(col_idx)
        for cell in ws[col_letter]:
            val = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)


def write_diagnostics(wb, counters: Dict[str, int], grouped_date: str, mode: str) -> None:
    if DIAGNOSTICS_SHEET in wb.sheetnames:
        wb.remove(wb[DIAGNOSTICS_SHEET])
    ws = wb.create_sheet(DIAGNOSTICS_SHEET)
    rows = [
        ("Metric", "Value"),
        ("total_tickers_in_universe", counters["total_tickers_in_universe"]),
        ("tickers_with_valid_polygon_data", counters["tickers_with_valid_polygon_data"]),
        ("excluded_by_insufficient_history", counters["excluded_by_insufficient_history"]),
        ("excluded_by_price_filter", counters["excluded_by_price_filter"]),
        ("excluded_by_liquidity_filter", counters["excluded_by_liquidity_filter"]),
        ("excluded_by_trend_filter", counters["excluded_by_trend_filter"]),
        ("excluded_by_momentum_filter", counters["excluded_by_momentum_filter"]),
        ("final_candidate_count", counters["final_candidate_count"]),
        ("mode", mode),
        ("grouped_date", grouped_date),
    ]
    for r in rows:
        ws.append(list(r))
    autosize_columns(ws)


def write_output(
    df: pd.DataFrame,
    template_file: str,
    output_file: str,
    grouped_date: str,
    counters: Dict[str, int],
    mode: str,
) -> None:
    wb = load_workbook(template_file)
    if BUYNOW_SHEET in wb.sheetnames:
        idx = wb.sheetnames.index(BUYNOW_SHEET)
        wb.remove(wb[BUYNOW_SHEET])
        ws = wb.create_sheet(BUYNOW_SHEET, idx)
    else:
        ws = wb.create_sheet(BUYNOW_SHEET)

    ws.append(list(df.columns))
    for _, row in df.iterrows():
        ws.append(row.tolist())
    autosize_columns(ws)
    ws["Z1"] = (
        f"momentum_master_v3.py | utc={datetime.now(timezone.utc).isoformat()} | grouped_date={grouped_date} | "
        f"mode={mode}"
    )

    write_diagnostics(wb, counters, grouped_date, mode)
    wb.save(output_file)


def main() -> None:
    setup_logging()
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing POLYGON_API_KEY environment variable")
    if not os.path.exists(INPUT_TEMPLATE):
        raise FileNotFoundError(f"Missing input template: {INPUT_TEMPLATE}")

    tickers = read_universe(INPUT_TEMPLATE)
    portfolio_value_sek = read_portfolio_value_sek(INPUT_TEMPLATE)
    counters = {
        "total_tickers_in_universe": len(tickers),
        "tickers_with_valid_polygon_data": 0,
        "excluded_by_insufficient_history": 0,
        "excluded_by_price_filter": 0,
        "excluded_by_liquidity_filter": 0,
        "excluded_by_trend_filter": 0,
        "excluded_by_momentum_filter": 0,
        "final_candidate_count": 0,
    }

    client = PolygonClient(api_key)
    grouped_date = pick_grouped_date_with_fx(client)
    start_date = (datetime.fromisoformat(grouped_date).date() - timedelta(days=600)).isoformat()
    fx = client.fetch_grouped_close(grouped_date, "USD", "SEK")

    valid_metrics: List[StockMetrics] = []
    for ticker in tickers:
        try:
            bars = client.fetch_daily_bars(ticker, start_date, grouped_date)
            m = compute_metrics(ticker, bars, counters)
            if m is not None:
                valid_metrics.append(m)
        except Exception as exc:
            logging.warning("%s skipped due to error: %s", ticker, exc)

    if len(valid_metrics) == 0:
        counters["final_candidate_count"] = 0
        raise RuntimeError("Zero valid candidates after processing universe")

    counters["final_candidate_count"] = len(valid_metrics)
    mode = "normal_top15" if len(valid_metrics) >= TOP_N else f"warning_fewer_than_15_candidates({len(valid_metrics)})"
    if len(valid_metrics) < TOP_N:
        logging.warning("Only %d valid candidates passed all filters", len(valid_metrics))

    buynow_df = build_buynow_df(valid_metrics, fx, portfolio_value_sek)
    write_output(buynow_df, INPUT_TEMPLATE, OUTPUT_FILE, grouped_date, counters, mode)
    logging.info("Wrote %s with %d rows", OUTPUT_FILE, len(buynow_df))


if __name__ == "__main__":
    main()
