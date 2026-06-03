#!/usr/bin/env python3
from __future__ import annotations

import logging, math, os, time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

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
DEBUG_SHEET = "DebugTickers"
SECTOR_MAP_FILE = "sector_map.csv"

MIN_PRICE = 5.0
MIN_ADTV20 = 20_000_000.0
MAX_DIST_SMA50 = 15.0
MAX_PER_SECTOR = 3
TOP_N = 15
TOP10_N = 10

@dataclass
class StockMetrics:
    ticker: str
    sector: str
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
    def __init__(self, key: str) -> None:
        self.key = key
        self.session = requests.Session()
        self.grouped_cache: Dict[str, Dict[str, Dict[str, float]]] = {}

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        merged = {"api" + "Key": self.key}
        if params:
            merged.update(params)
        url = f"{POLYGON_BASE}{path}"
        for attempt in range(1, 7):
            try:
                r = self.session.get(url, params=merged, timeout=30)
                if r.status_code == 429:
                    wait = min(75, 10 * attempt)
                    logging.warning("Polygon rate limit. Waiting %ss and retrying (%s/6).", wait, attempt)
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                if data.get("status") == "ERROR":
                    raise RuntimeError(f"Polygon error: {data}")
                return data
            except Exception:
                if attempt >= 6:
                    raise
                time.sleep(min(30, 3 * attempt))
        raise RuntimeError("Polygon request failed")

    def fetch_fx_close(self, date_str: str) -> float:
        data = self._get(f"/v2/aggs/ticker/C:USDSEK/range/1/day/{date_str}/{date_str}", {"adjusted": "true", "limit": 10})
        results = data.get("results", []) or []
        if not results:
            raise ValueError(f"No USDSEK result for {date_str}")
        return float(results[-1]["c"])

    def fetch_grouped_stocks(self, date_str: str) -> Dict[str, Dict[str, float]]:
        if date_str in self.grouped_cache:
            return self.grouped_cache[date_str]
        data = self._get(f"/v2/aggs/grouped/locale/us/market/stocks/{date_str}", {"adjusted": "true"})
        out: Dict[str, Dict[str, float]] = {}
        for row in data.get("results", []) or []:
            ticker = str(row.get("T", "")).upper().strip()
            close = row.get("c")
            volume = row.get("v")
            if ticker and close is not None and volume is not None:
                out[ticker] = {"close": float(close), "volume": float(volume)}
        self.grouped_cache[date_str] = out
        return out

def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

def normalize_ticker(ticker: str) -> str:
    return str(ticker).strip().upper()

def alt_ticker(ticker: str) -> str:
    return normalize_ticker(ticker).replace(".", "-")

def get_from_map(day_map: Dict[str, Dict[str, float]], ticker: str) -> Optional[Dict[str, float]]:
    return day_map.get(normalize_ticker(ticker)) or day_map.get(alt_ticker(ticker))

def read_universe(path: str) -> List[str]:
    df = pd.read_excel(path, sheet_name=UNIVERSE_SHEET)
    if "Ticker" not in df.columns:
        raise ValueError("Universe sheet must contain a 'Ticker' column")
    tickers = df["Ticker"].dropna().astype(str).str.strip().str.upper().replace("", np.nan).dropna().tolist()
    unique = list(dict.fromkeys(tickers))
    if not unique:
        raise ValueError("No tickers found in Universe sheet")
    return unique

def read_sector_map(path: str = SECTOR_MAP_FILE) -> Dict[str, str]:
    if not os.path.exists(path):
        logging.warning("%s missing. Sector will be Unknown.", path)
        return {}
    df = pd.read_csv(path)
    if "Ticker" not in df.columns or "Sector" not in df.columns:
        logging.warning("%s must contain Ticker and Sector columns. Ignoring sector map.", path)
        return {}
    sector_map: Dict[str, str] = {}
    for _, row in df.iterrows():
        ticker = normalize_ticker(row.get("Ticker", ""))
        sector = str(row.get("Sector", "")).strip()
        if ticker and sector and sector.lower() != "nan":
            sector_map[ticker] = sector
            sector_map[alt_ticker(ticker)] = sector
    logging.info("Loaded %d sector keys from %s", len(sector_map), path)
    return sector_map

def read_portfolio_value_sek(path: str) -> float:
    wb = load_workbook(path, data_only=True)
    value = wb[PARAM_SHEET]["B1"].value
    if value is None:
        raise ValueError("Parametrar!B1 is empty")
    parsed = float(value)
    if parsed <= 0:
        raise ValueError("Parametrar!B1 must be > 0")
    return parsed

def pick_latest_grouped_date(client: PolygonClient, max_lookback_days: int = 10) -> Tuple[str, Dict[str, Dict[str, float]], float]:
    today = datetime.now(timezone.utc).date()
    for days_back in range(1, max_lookback_days + 1):
        date_str = (today - timedelta(days=days_back)).isoformat()
        try:
            grouped = client.fetch_grouped_stocks(date_str)
            fx = client.fetch_fx_close(date_str)
            if len(grouped) > 1000:
                return date_str, grouped, fx
        except Exception as exc:
            logging.info("Grouped date %s unavailable: %s", date_str, exc)
    raise RuntimeError("Could not find recent grouped stock data with USDSEK")

def find_grouped_near(client: PolygonClient, target_date, max_back_days: int = 10) -> Tuple[str, Dict[str, Dict[str, float]]]:
    for days_back in range(0, max_back_days + 1):
        date_str = (target_date - timedelta(days=days_back)).isoformat()
        try:
            grouped = client.fetch_grouped_stocks(date_str)
            if len(grouped) > 1000:
                return date_str, grouped
        except Exception:
            continue
    raise RuntimeError(f"Could not find grouped data near {target_date}")

def collect_recent_trading_maps(client: PolygonClient, latest_date: str, needed: int = 20) -> List[Tuple[str, Dict[str, Dict[str, float]]]]:
    latest = datetime.fromisoformat(latest_date).date()
    maps: List[Tuple[str, Dict[str, Dict[str, float]]]] = []
    days_back = 0
    while len(maps) < needed and days_back < 45:
        date_str = (latest - timedelta(days=days_back)).isoformat()
        try:
            grouped = client.fetch_grouped_stocks(date_str)
            if len(grouped) > 1000:
                maps.append((date_str, grouped))
        except Exception:
            pass
        days_back += 1
    if len(maps) < needed:
        raise RuntimeError(f"Only found {len(maps)} recent trading maps, need {needed}")
    return maps

def pct_return(current: float, old: Optional[float]) -> Optional[float]:
    if old is None or old <= 0:
        return None
    return (current / old - 1.0) * 100.0

def build_metrics(tickers, latest_map, recent20, anchor_maps, sector_map):
    counters = {
        "total_tickers_in_universe": len(tickers),
        "sector_mappings_loaded": len(sector_map),
        "grouped_data_pipeline": 1,
        "latest_grouped_symbols": len(latest_map),
        "successful_polygon_data": 0,
        "no_data_from_polygon": 0,
        "excluded_by_insufficient_history": 0,
        "excluded_by_price_filter": 0,
        "excluded_by_liquidity_filter": 0,
        "excluded_by_trend_filter": 0,
        "excluded_by_momentum_filter": 0,
        "excluded_by_overextended_filter": 0,
        "excluded_by_negative_5d_filter": 0,
        "final_candidate_count": 0,
    }
    metrics: List[StockMetrics] = []
    debug_rows = []
    for ticker in tickers:
        sector = sector_map.get(normalize_ticker(ticker)) or sector_map.get(alt_ticker(ticker)) or "Unknown"
        latest = get_from_map(latest_map, ticker)
        if not latest:
            counters["no_data_from_polygon"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "NO_LATEST_DATA"})
            continue
        counters["successful_polygon_data"] += 1
        price = float(latest["close"])
        if price < MIN_PRICE:
            counters["excluded_by_price_filter"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "PRICE", "LastClose": price})
            continue
        dollar_values = []
        for _, grouped in recent20:
            row = get_from_map(grouped, ticker)
            if row:
                dollar_values.append(float(row["close"]) * float(row["volume"]))
        if len(dollar_values) < 10:
            counters["excluded_by_insufficient_history"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "INSUFFICIENT_20D", "RowsReturned": len(dollar_values), "LastClose": price})
            continue
        adv20 = float(np.mean(dollar_values))
        if adv20 < MIN_ADTV20:
            counters["excluded_by_liquidity_filter"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "LIQUIDITY", "LastClose": price, "AvgDollarVolume20": adv20})
            continue
        def close_at(key: str) -> Optional[float]:
            row = get_from_map(anchor_maps[key], ticker)
            return float(row["close"]) if row else None
        c5, c21, c63, c126, c252 = close_at("ret5d"), close_at("ret1m"), close_at("ret3m"), close_at("ret6m"), close_at("ret12m")
        c50, c200 = close_at("sma50_proxy"), close_at("sma200_proxy")
        if None in [c5, c21, c63, c126, c252, c50, c200]:
            counters["excluded_by_insufficient_history"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "MISSING_ANCHOR", "LastClose": price})
            continue
        sma50, sma200 = float(c50), float(c200)
        if not (price > sma50 and price > sma200):
            counters["excluded_by_trend_filter"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "TREND", "LastClose": price, "SMA50": sma50, "SMA200": sma200})
            continue
        ret5d, ret1m, ret3m = pct_return(price, c5), pct_return(price, c21), pct_return(price, c63)
        ret6m, ret12m = pct_return(price, c126), pct_return(price, c252)
        if None in [ret5d, ret1m, ret3m, ret6m, ret12m]:
            counters["excluded_by_insufficient_history"] += 1
            continue
        if ret5d <= 0:
            counters["excluded_by_negative_5d_filter"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "NEGATIVE_5D", "LastClose": price, "Ret5d": ret5d})
            continue
        if not (ret3m > 0 and ret6m > 0 and ret12m > 0):
            counters["excluded_by_momentum_filter"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "MOMENTUM", "LastClose": price, "Ret3m": ret3m, "Ret6m": ret6m, "Ret12m": ret12m})
            continue
        dist_sma50 = (price / sma50 - 1.0) * 100.0
        if dist_sma50 > MAX_DIST_SMA50:
            counters["excluded_by_overextended_filter"] += 1
            debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "OVEREXTENDED", "LastClose": price, "Dist_SMA50": dist_sma50})
            continue
        accel = float(ret1m - ret3m)
        stock_momentum = 0.25 * ret1m + 0.35 * ret3m + 0.25 * ret6m + 0.15 * ret12m
        total_score = stock_momentum + 0.10 * accel
        metrics.append(StockMetrics(ticker, sector, price, adv20, sma50, sma200, ret5d, ret1m, ret3m, ret6m, ret12m, accel, dist_sma50, total_score))
        debug_rows.append({"Ticker": ticker, "Sector": sector, "Status": "PASS", "LastClose": price, "AvgDollarVolume20": adv20, "Ret5d": ret5d, "Ret1m": ret1m, "Ret3m": ret3m, "Ret6m": ret6m, "Ret12m": ret12m, "Dist_SMA50": dist_sma50, "TotalScore": total_score})
    counters["final_candidate_count"] = len(metrics)
    return metrics, counters, pd.DataFrame(debug_rows[:300])

def build_buynow_df(metrics: List[StockMetrics], fx: float, portfolio_value_sek: float) -> pd.DataFrame:
    ranked_all = sorted(metrics, key=lambda x: x.total_score, reverse=True)
    selected, sector_counts = [], {}
    for metric in ranked_all:
        if metric.sector != "Unknown" and sector_counts.get(metric.sector, 0) >= MAX_PER_SECTOR:
            continue
        selected.append(metric)
        if metric.sector != "Unknown":
            sector_counts[metric.sector] = sector_counts.get(metric.sector, 0) + 1
        if len(selected) >= TOP_N:
            break
    rows, position_size_sek = [], portfolio_value_sek / TOP10_N
    for rank, metric in enumerate(selected, start=1):
        is_top10 = rank <= TOP10_N
        price_sek = metric.price_usd * fx
        qty = max(1, math.floor(position_size_sek / price_sek)) if is_top10 else ""
        rows.append({"Rank": rank, "Ticker": metric.ticker, "Sector": metric.sector, "Top10": bool(is_top10), "Qty": qty, "Price_USD": metric.price_usd, "FX": fx, "Price_SEK": price_sek, "Position_SEK": qty * price_sek if is_top10 else "", "AvgDollarVolume20": metric.avg_dollar_volume20, "SMA50": metric.sma50, "SMA200": metric.sma200, "Ret5d": metric.ret5d, "Ret1m": metric.ret1m, "Ret3m": metric.ret3m, "Ret6m": metric.ret6m, "Ret12m": metric.ret12m, "Dist_SMA50": metric.dist_sma50, "Accel": metric.accel, "TotalScore": metric.total_score})
    return pd.DataFrame(rows)

def autosize_columns(ws) -> None:
    if ws.max_row < 1:
        return
    for col_idx, _ in enumerate(ws[1], start=1):
        col_letter = get_column_letter(col_idx)
        max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in ws[col_letter])
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)

def replace_sheet_with_df(wb, name: str, df: pd.DataFrame, index: Optional[int] = None) -> None:
    if name in wb.sheetnames:
        old_index = wb.sheetnames.index(name)
        wb.remove(wb[name])
        ws = wb.create_sheet(name, old_index if index is None else index)
    else:
        ws = wb.create_sheet(name, index)
    ws.append(list(df.columns))
    for _, row in df.iterrows():
        ws.append(row.tolist())
    autosize_columns(ws)

def write_output(df, debug_df, template_file, output_file, grouped_date, counters, mode):
    wb = load_workbook(template_file)
    buynow_index = wb.sheetnames.index(BUYNOW_SHEET) if BUYNOW_SHEET in wb.sheetnames else None
    replace_sheet_with_df(wb, BUYNOW_SHEET, df, buynow_index)
    wb[BUYNOW_SHEET]["Z1"] = f"momentum_master_v3.py | grouped_refined_sector_pipeline | utc={datetime.now(timezone.utc).isoformat()} | grouped_date={grouped_date} | mode={mode} | max_per_sector={MAX_PER_SECTOR}"
    diag_df = pd.DataFrame(list(counters.items()) + [("mode", mode), ("grouped_date", grouped_date), ("max_per_sector", MAX_PER_SECTOR)], columns=["Metric", "Value"])
    replace_sheet_with_df(wb, DIAGNOSTICS_SHEET, diag_df)
    replace_sheet_with_df(wb, DEBUG_SHEET, debug_df)
    wb.save(output_file)

def main() -> None:
    setup_logging()
    key = os.getenv("POLYGON_" + "API_KEY")
    if not key:
        raise EnvironmentError("Missing Polygon key environment variable")
    if not os.path.exists(INPUT_TEMPLATE):
        raise FileNotFoundError(f"Missing input template: {INPUT_TEMPLATE}")
    tickers = read_universe(INPUT_TEMPLATE)
    sector_map = read_sector_map(SECTOR_MAP_FILE)
    portfolio_value = read_portfolio_value_sek(INPUT_TEMPLATE)
    client = PolygonClient(key)
    latest_date, latest_map, fx = pick_latest_grouped_date(client)
    latest_dt = datetime.fromisoformat(latest_date).date()
    logging.info("Using grouped stock date %s with %d symbols, USDSEK %.4f", latest_date, len(latest_map), fx)
    recent20 = collect_recent_trading_maps(client, latest_date, 20)
    anchor_targets = {"ret5d": latest_dt - timedelta(days=7), "ret1m": latest_dt - timedelta(days=30), "ret3m": latest_dt - timedelta(days=91), "ret6m": latest_dt - timedelta(days=182), "ret12m": latest_dt - timedelta(days=365), "sma50_proxy": latest_dt - timedelta(days=75), "sma200_proxy": latest_dt - timedelta(days=300)}
    anchor_maps = {}
    for name, target in anchor_targets.items():
        date_str, grouped = find_grouped_near(client, target)
        logging.info("Anchor %s uses %s with %d symbols", name, date_str, len(grouped))
        anchor_maps[name] = grouped
    metrics, counters, debug_df = build_metrics(tickers, latest_map, recent20, anchor_maps, sector_map)
    if not metrics:
        raise RuntimeError("Zero valid candidates after grouped refined sector processing")
    mode = "normal_top15" if len(metrics) >= TOP_N else f"warning_fewer_than_15_candidates({len(metrics)})"
    buynow = build_buynow_df(metrics, fx, portfolio_value)
    write_output(buynow, debug_df, INPUT_TEMPLATE, OUTPUT_FILE, latest_date, counters, mode)
    logging.info("Wrote %s with %d BuyNow rows. Candidates before top cut: %d", OUTPUT_FILE, len(buynow), len(metrics))

if __name__ == "__main__":
    main()
