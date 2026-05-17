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
MAX_DIST_SMA50 = 15.0
TOP_N = 15
TOP10_N = 10


@dataclass
class StockMetrics:
    ticker: str
    price_usd: float
    avg_dollar_volume20: float
    sma50: float
    sma200: float
    ret5d: float
    ret1m: float
    ret3m: float
    ret6m: float
    ret12m: float
    accel: float
    dist_sma50: float
    total_score: float


class PolygonClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = requests.Session()

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        merged = {"apiKey": self.api_key}
        if params:
            merged.update(params)

        response = self.session.get(
            f"{POLYGON_BASE}{path}",
            params=merged,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "ERROR":  # Polygon error payload
            raise RuntimeError(str(data))

        return data

    def fetch_grouped_snapshot(self, date_str: str) -> Dict[str, Dict]:
        data = self._get(
            f"/v2/aggs/grouped/locale/us/market/stocks/{date_str}",
            {"adjusted": "true"},
        )

        result = {}
        for row in data.get("results", []):
            ticker = row.get("T")
            if ticker:
                result[ticker] = row
        return result

    def fetch_grouped_fx(self, date_str: str) -> float:
        data = self._get(
            f"/v2/aggs/ticker/C:USDSEK/range/1/day/{date_str}/{date_str}",
            {"adjusted": "true"},
        )
        results = data.get("results", [])
        if not results:
            raise RuntimeError("No USDSEK data")
        return float(results[-1]["c"])

    def fetch_daily_bars(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        data = self._get(
            f"/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}",
            {
                "adjusted": "true",
                "sort": "asc",
                "limit": 5000,
            },
        )

        rows = data.get("results", [])
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df = df.rename(columns={
            "c": "close",
            "v": "volume",
        })
        return df[["close", "volume"]].copy()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def read_universe(path: str) -> List[str]:
    df = pd.read_excel(path, sheet_name=UNIVERSE_SHEET)

    if "Ticker" not in df.columns:
        raise ValueError("Universe sheet must contain column 'Ticker'")

    tickers = (
        df["Ticker"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .replace("", np.nan)
        .dropna()
        .tolist()
    )

    return list(dict.fromkeys(tickers))


def read_portfolio_value_sek(path: str) -> float:
    wb = load_workbook(path, data_only=True)
    value = wb[PARAM_SHEET]["B1"].value

    if value is None:
        raise ValueError("Parametrar!B1 is empty")

    value = float(value)

    if value <= 0:
        raise ValueError("Parametrar!B1 must be > 0")

    return value


def pick_grouped_date_with_data(client: PolygonClient, max_lookback_days: int = 7) -> str:
    today = datetime.now(timezone.utc).date()

    for delta in range(1, max_lookback_days + 1):
        d = (today - timedelta(days=delta)).isoformat()
        try:
            snapshot = client.fetch_grouped_snapshot(d)
            if len(snapshot) > 5000:
                return d
        except Exception:
            pass

    raise RuntimeError("Could not find valid grouped market date")


def compute_metrics(ticker: str, bars: pd.DataFrame) -> Optional[StockMetrics]:
    if len(bars) < 253:
        return None

    closes = bars["close"].astype(float).reset_index(drop=True)
    volumes = bars["volume"].astype(float).reset_index(drop=True)

    if closes.isna().any() or volumes.isna().any():
        return None

    price = float(closes.iloc[-1])

    if price < MIN_PRICE:
        return None

    adv20 = float((closes.iloc[-20:] * volumes.iloc[-20:]).mean())

    if adv20 < MIN_ADTV20:
        return None

    sma50 = float(closes.iloc[-50:].mean())
    sma200 = float(closes.iloc[-200:].mean())

    if not (price > sma50 > sma200):
        return None

    ret5d = (price / float(closes.iloc[-6]) - 1.0) * 100.0
    ret1m = (price / float(closes.iloc[-22]) - 1.0) * 100.0
    ret3m = (price / float(closes.iloc[-64]) - 1.0) * 100.0
    ret6m = (price / float(closes.iloc[-127]) - 1.0) * 100.0
    ret12m = (price / float(closes.iloc[-253]) - 1.0) * 100.0

    if not (ret3m > 0 and ret6m > 0 and ret12m > 0):
        return None

    if ret5d <= 0:
        return None

    dist_sma50 = (price / sma50 - 1.0) * 100.0

    if dist_sma50 > MAX_DIST_SMA50:
        return None

    accel = ret1m - ret3m

    stock_momentum = (
        0.25 * ret1m
        + 0.35 * ret3m
        + 0.25 * ret6m
        + 0.15 * ret12m
    )

    total_score = stock_momentum + 0.10 * accel

    return StockMetrics(
        ticker=ticker,
        price_usd=price,
        avg_dollar_volume20=adv20,
        sma50=sma50,
        sma200=sma200,
        ret5d=ret5d,
        ret1m=ret1m,
        ret3m=ret3m,
        ret6m=ret6m,
        ret12m=ret12m,
        accel=accel,
        dist_sma50=dist_sma50,
        total_score=total_score,
    )


def build_buynow_df(metrics: List[StockMetrics], fx: float, portfolio_value_sek: float) -> pd.DataFrame:
    ranked = sorted(metrics, key=lambda x: x.total_score, reverse=True)[:TOP_N]

    position_size_sek = portfolio_value_sek / TOP10_N

    rows = []

    for rank, m in enumerate(ranked, start=1):
        is_top10 = rank <= TOP10_N
        price_sek = m.price_usd * fx

        qty = ""
        if is_top10:
            qty = max(1, math.floor(position_size_sek / price_sek))

        rows.append({
            "Rank": rank,
            "Ticker": m.ticker,
            "Top10": is_top10,
            "Qty": qty,
            "Price_USD": m.price_usd,
            "FX": fx,
            "Price_SEK": price_sek,
            "Position_SEK": position_size_sek if is_top10 else "",
            "AvgDollarVolume20": m.avg_dollar_volume20,
            "SMA50": m.sma50,
            "SMA200": m.sma200,
            "Ret5d": m.ret5d,
            "Ret1m": m.ret1m,
            "Ret3m": m.ret3m,
            "Ret6m": m.ret6m,
            "Ret12m": m.ret12m,
            "Dist_SMA50": m.dist_sma50,
            "Accel": m.accel,
            "TotalScore": m.total_score,
        })

    return pd.DataFrame(rows)


def autosize_columns(ws) -> None:
    for col_idx in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0

        for cell in ws[col_letter]:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))

        ws.column_dimensions[col_letter].width = min(max_len + 2, 40)


def write_sheet(wb, sheet_name: str, df: pd.DataFrame) -> None:
    if sheet_name in wb.sheetnames:
        index = wb.sheetnames.index(sheet_name)
        wb.remove(wb[sheet_name])
        ws = wb.create_sheet(sheet_name, index)
    else:
        ws = wb.create_sheet(sheet_name)

    if not df.empty:
        ws.append(list(df.columns))
        for _, row in df.iterrows():
            ws.append(row.tolist())

    autosize_columns(ws)


def main() -> None:
    setup_logging()

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError("Missing POLYGON_API_KEY")

    tickers = read_universe(INPUT_TEMPLATE)
    portfolio_value_sek = read_portfolio_value_sek(INPUT_TEMPLATE)

    client = PolygonClient(api_key)

    grouped_date = pick_grouped_date_with_data(client)
    fx = client.fetch_grouped_fx(grouped_date)

    start_date = (
        datetime.fromisoformat(grouped_date).date() - timedelta(days=600)
    ).isoformat()

    metrics = []

    for i, ticker in enumerate(tickers, start=1):
        if i % 100 == 0:
            logging.info("Processing %d / %d", i, len(tickers))

        try:
            bars = client.fetch_daily_bars(ticker, start_date, grouped_date)
            if bars.empty:
                continue

            m = compute_metrics(ticker, bars)
            if m:
                metrics.append(m)

        except Exception:
            continue

    if not metrics:
        raise RuntimeError("No valid momentum candidates found")

    buynow_df = build_buynow_df(metrics, fx, portfolio_value_sek)

    wb = load_workbook(INPUT_TEMPLATE)
    write_sheet(wb, BUYNOW_SHEET, buynow_df)

    diagnostics = pd.DataFrame([
        ["total_tickers_in_universe", len(tickers)],
        ["successful_polygon_data", len(metrics)],
        ["final_candidate_count", len(metrics)],
        ["mode", "normal_top15"],
        ["grouped_date", grouped_date],
    ], columns=["Metric", "Value"])

    write_sheet(wb, DIAGNOSTICS_SHEET, diagnostics)

    wb[BUYNOW_SHEET]["Z1"] = (
        f"momentum_master_v3.py | "
        f"utc={datetime.now(timezone.utc).isoformat()} | "
        f"grouped_date={grouped_date}"
    )

    wb.save(OUTPUT_FILE)

    logging.info("Wrote %s with %d BuyNow rows", OUTPUT_FILE, len(buynow_df))


if __name__ == "__main__":
    main()
