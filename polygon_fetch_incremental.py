import os, time, datetime as dt
import pandas as pd
import requests
from pathlib import Path

BASE = Path(".")
DATA = BASE
TICKERS_CSV = BASE / "tickers.csv"
CACHE = DATA / "cache.parquet"
POLYGON_API_KEY = os.environ["POLYGON_API_KEY"]
POLY_URL = "https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{from_}/{to_}?adjusted=true&sort=asc&apiKey={key}"

def _today_yesterday():
    return (dt.date.today() - dt.timedelta(days=1))

def _ds(d: dt.date) -> str:
    return d.strftime("%Y-%m-%d")

def _last_date(df_t):
    if df_t.empty: return None
    return pd.to_datetime(df_t["date"]).dt.date.max()

def _fetch(t, start_date, end_date):
    if start_date is None:
        start_date = end_date - dt.timedelta(days=365*5)
    if start_date > end_date:
        return pd.DataFrame()
    url = POLY_URL.format(ticker=t, from_=_ds(start_date), to_=_ds(end_date), key=POLYGON_API_KEY)
    for attempt in range(3):
        r = requests.get(url, timeout=60)
        if r.status_code == 429:
            time.sleep(2 + 2*attempt); continue
        r.raise_for_status()
        js = r.json()
        res = js.get("results", [])
        if not res: return pd.DataFrame()
        df = pd.DataFrame(res)
        df["Ticker"] = t
        df["date"] = pd.to_datetime(df["t"], unit="ms").dt.tz_localize("UTC").dt.date
        df.rename(columns={"c":"Close","o":"Open","h":"High","l":"Low","v":"Volume"}, inplace=True)
        return df[["Ticker","date","Open","High","Low","Close","Volume"]].drop_duplicates(["Ticker","date"]).sort_values("date")
    return pd.DataFrame()

def main():
    tickers = pd.read_csv(TICKERS_CSV, header=None, names=["Ticker"])
    tickers["Ticker"] = tickers["Ticker"].str.strip().str.upper()
    tickers = tickers[tickers["Ticker"] != ""]
    if CACHE.exists():
        cache = pd.read_parquet(CACHE)
    else:
        cache = pd.DataFrame(columns=["Ticker","date","Open","High","Low","Close","Volume"])
    if not cache.empty:
        cache["date"] = pd.to_datetime(cache["date"]).dt.date
        cache = cache.drop_duplicates(["Ticker","date"])

    end_date = _today_yesterday()
    parts = []
    for i, t in enumerate(tickers["Ticker"], 1):
        existing = cache[cache["Ticker"] == t] if not cache.empty else pd.DataFrame()
        last_dt = _last_date(existing)
        start_dt = (last_dt + dt.timedelta(days=1)) if last_dt else None
        fresh = _fetch(t, start_dt, end_date)
        if not fresh.empty:
            parts.append(fresh)
        if i % 50 == 0: time.sleep(1.0)

    to_concat = [cache] if not cache.empty else []
    if parts:
        to_concat.append(pd.concat(parts, ignore_index=True))
    final = pd.concat(to_concat, ignore_index=True) if to_concat else cache
    final = final.drop_duplicates(["Ticker","date"]).sort_values(["Ticker","date"])

    # ✅ Spara ENDAST i parquet (ingen gigantisk Excel längre)
    final.to_parquet(CACHE, index=False)

if __name__ == "__main__":
    main()
