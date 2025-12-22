import os, sys, shutil, datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "").strip()

SECTOR_MAP_FILE = Path("public/data/sector_map.csv")

TARGET_POSITIONS = 10
DEFAULT_MIN_PRICE_USD = 5.0

def log(msg: str) -> None:
    print(msg, flush=True)

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def today_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d")

def backup_template(src: Path) -> None:
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ','_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst}")

def read_param_value(path: Path, label_substr: str, default=None, numeric=True):
    try:
        df = pd.read_excel(path, sheet_name="Parametrar", header=None)
        mask = df[0].astype(str).str.lower().str.contains(str(label_substr).lower(), na=False)
        if mask.any():
            val = df.loc[mask, 1].iloc[0]
            if numeric:
                v = pd.to_numeric(val, errors="coerce")
                return default if pd.isna(v) else float(v)
            return str(val)
    except Exception as e:
        log(f"[WARN] Parametrar läsning '{label_substr}' misslyckades: {e}")
    return default

def polygon_prev_trading_dates() -> list[str]:
    d = dt.datetime.utcnow().date() - dt.timedelta(days=1)
    return [(d - dt.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10)]

def polygon_grouped_close_map(date_yyyy_mm_dd: str) -> dict[str, float]:
    if not POLYGON_API_KEY:
        raise RuntimeError("POLYGON_API_KEY saknas")
    url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_yyyy_mm_dd}"
    r = requests.get(url, params={"adjusted": "true", "apiKey": POLYGON_API_KEY}, timeout=30)
    r.raise_for_status()
    js = r.json()
    results = js.get("results", []) or []
    mp = {}
    for row in results:
        t = row.get("T")
        c = row.get("c")
        if t and c:
            mp[str(t).upper()] = float(c)
    return mp

def get_usdsek_prev() -> float:
    if not POLYGON_API_KEY:
        return 10.0
    try:
        r = requests.get(
            "https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
            params={"adjusted":"true","limit":1,"apiKey":POLYGON_API_KEY},
            timeout=10
        )
        r.raise_for_status()
        res = r.json().get("results", [])
        if res and res[0].get("c"):
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] USDSEK polygon misslyckades: {e}")
    return 10.0

def merge_sector_map(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if SECTOR_MAP_FILE.exists():
        sm = pd.read_csv(SECTOR_MAP_FILE)
        if "Ticker" in sm.columns:
            sm["Ticker"] = sm["Ticker"].astype(str).str.upper().str.strip()
            sm = sm.drop_duplicates(subset=["Ticker"])
            keep = [c for c in ["Ticker","Sector","Industry"] if c in sm.columns]
            df = df.merge(sm[keep], on="Ticker", how="left")
    if "Sector" not in df.columns:
        df["Sector"] = "Unknown"
    if "Industry" not in df.columns:
        df["Industry"] = ""
    df["Sector"] = df["Sector"].fillna("Unknown")
    df["Industry"] = df["Industry"].fillna("")
    return df

def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # idempotent
    for c in ["StockMomentum","Accel","SectorMomentum","SectorZ","TotalScore"]:
        if c in df.columns:
            df = df.drop(columns=[c])

    for col in ["Ret1m","Ret3m","Ret6m"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")

    r1 = df["Ret1m"].fillna(0.0)
    r3 = df["Ret3m"].fillna(0.0)
    r6 = df["Ret6m"].fillna(0.0)

    df["StockMomentum"] = 0.50*r1 + 0.30*r3 + 0.20*r6
    df["Accel"] = r1 - r3

    if "Sector" not in df.columns:
        df["Sector"] = "Unknown"

    sect = (
        df.groupby("Sector", dropna=False)
          .agg(SectorMomentum=("StockMomentum","median"))
          .reset_index()
    )
    df = df.merge(sect, on="Sector", how="left")

    sm = df["SectorMomentum"].fillna(0.0)
    if sm.std(ddof=0) > 0:
        z = (sm - sm.mean()) / sm.std(ddof=0)
    else:
        z = sm*0.0
    df["SectorZ"] = z

    df["TotalScore"] = 0.75*df["StockMomentum"].fillna(0.0) + 0.20*df["SectorZ"].fillna(0.0) + 0.05*df["Accel"].fillna(0.0)
    return df

def diagnose_counts(df: pd.DataFrame, label: str):
    log(f"[DIAG] {label}: rows={len(df)}")
    if len(df) == 0:
        return
    for c in ["Price_USD","Ret1m","Ret3m","Ret6m","SMA50","SMA200","TotalScore"]:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            log(f"[DIAG]  - {c}: non-null={int(s.notna().sum())} | >0={int((s>0).sum())}")

def build_buynow(df_ec: pd.DataFrame, portval_sek: float, usdsek: float, min_price_usd: float, close_map: dict[str,float]):
    df = df_ec.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if "Ticker" not in df.columns:
        raise RuntimeError("EarlyCandidates saknar kolumn 'Ticker'")

    need = ["Ret1m","Ret3m","Ret6m","SMA50","SMA200"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise RuntimeError(f"EarlyCandidates saknar: {missing}")

    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df = df[df["Ticker"].str.len() > 0]

    df["Price_USD"] = df["Ticker"].map(close_map)
    df["Price_USD"] = pd.to_numeric(df["Price_USD"], errors="coerce")
    df = df.dropna(subset=["Price_USD"])
    df = df[(df["Price_USD"] > 0) & (df["Price_USD"] >= float(min_price_usd))]

    df = merge_sector_map(df)

    # numerik
    for c in ["Ret1m","Ret3m","Ret6m","SMA50","SMA200"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = compute_scores(df)
    diagnose_counts(df, "Efter pris+score")

    # --------- FILTERLÄGEN ----------
    # 1) Strict trend + ret3m + accel
    strict = df.dropna(subset=["SMA50","SMA200","Ret1m","Ret3m"]).copy()
    strict = strict[(strict["SMA200"] > 0) & (strict["Price_USD"] >= strict["SMA200"]) & (strict["SMA50"] > strict["SMA200"])]
    strict = strict[strict["Ret3m"] > 0]
    strict = strict[strict["Ret1m"] > strict["Ret3m"]]
    log(f"[INFO] Strict count = {len(strict)}")

    mode = "strict"
    work = strict

    # 2) Relax trend, släpp accel
    if work.empty:
        relaxed = df.dropna(subset=["SMA50","SMA200","Ret3m"]).copy()
        relaxed = relaxed[(relaxed["SMA200"] > 0) & (relaxed["Price_USD"] >= relaxed["SMA200"]) & (relaxed["SMA50"] > relaxed["SMA200"])]
        relaxed = relaxed[relaxed["Ret3m"] > 0]
        log(f"[WARN] Strict tom. Relax(trend+Ret3m) count = {len(relaxed)}")
        mode = "relaxed_trend"
        work = relaxed

    # 3) Om SMA verkar “fel”: kör momentum utan SMA
    if work.empty:
        mom_only = df.dropna(subset=["Ret3m","Ret6m"]).copy()
        mom_only = mom_only[(mom_only["Ret3m"] > 0) & (mom_only["Ret6m"] > 0)]
        log(f"[WARN] Trend tomt. Momentum-only (Ret3m>0 & Ret6m>0) count = {len(mom_only)}")
        mode = "momentum_only"
        work = mom_only

    # 4) Sista fallback: ta top på TotalScore utan filter
    if work.empty:
        log("[WARN] Momentum-only tomt. Fallback: top TotalScore utan filter.")
        mode = "fallback_score"
        work = df.copy()

    work = work.sort_values("TotalScore", ascending=False).reset_index(drop=True)
    work["Rank"] = work.index + 1
    work["Top10"] = work["Rank"] <= 10
    work = work.head(15).copy()

    work["FX"] = float(usdsek)
    work["Price_SEK"] = work["Price_USD"] * float(usdsek)

    per_pos = (float(portval_sek) / TARGET_POSITIONS) if portval_sek and portval_sek > 0 else 0.0
    def qty(price_sek: float, top10: bool) -> int:
        if not top10:
            return 0
        if price_sek <= 0 or per_pos <= 0:
            return 0
        q = int(np.floor(per_pos / price_sek))
        return max(q, 1)

    work["Qty"] = [qty(p, t) for p, t in zip(work["Price_SEK"], work["Top10"])]
    work["Position_SEK"] = work["Qty"] * work["Price_SEK"]

    cols = [
        "Rank","Ticker","Top10","Qty",
        "Price_USD","FX","Price_SEK","Position_SEK",
        "Sector","Industry",
        "Ret1m","Ret3m","Ret6m","SMA50","SMA200",
        "StockMomentum","SectorMomentum","Accel","TotalScore",
    ]
    cols = [c for c in cols if c in work.columns]
    return work[cols].copy(), mode

def write_buynow_sheet(wb, df_out: pd.DataFrame, stamp: str):
    old_index = None
    for i, sh in enumerate(wb.worksheets):
        if sh.title == "BuyNow":
            old_index = i
            wb.remove(sh)
            break

    ws = wb.create_sheet("BuyNow")

    for c, h in enumerate(df_out.columns, 1):
        ws.cell(1, c, h)

    for r_idx, row in enumerate(df_out.itertuples(index=False), 2):
        for c_idx, val in enumerate(row, 1):
            ws.cell(r_idx, c_idx, val)

    for i, name in enumerate(df_out.columns, 1):
        w = 14
        ln = str(name).lower()
        if ln == "ticker":
            w = 10
        if ln in ("sector","industry"):
            w = 18
        ws.column_dimensions[get_column_letter(i)].width = w

    ws["Z1"] = stamp

    if old_index is not None:
        order = wb.worksheets[:]
        new_sheet = order.pop(-1)
        order.insert(old_index, new_sheet)
        wb._sheets = order

def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        sys.exit(f"Error: Mallen saknas: {TEMPLATE_FILE}")

    backup_template(tpl)

    portval   = read_param_value(tpl, "portföljvärde", default=0.0, numeric=True)
    min_price = read_param_value(tpl, "min pris", default=DEFAULT_MIN_PRICE_USD, numeric=True)
    usdsek    = get_usdsek_prev()

    log(f"[INFO] Portföljvärde(SEK) = {portval}")
    log(f"[INFO] Min pris (USD)    = {min_price}")
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    log("[STEP] Läser EarlyCandidates…")
    df_ec = pd.read_excel(tpl, sheet_name="EarlyCandidates")

    close_map = {}
    ok_date = None
    log("[STEP] Hämtar Polygon grouped priser…")
    for d in polygon_prev_trading_dates():
        try:
            close_map = polygon_grouped_close_map(d)
            if close_map:
                ok_date = d
                break
        except Exception as e:
            log(f"[WARN] Grouped fetch misslyckades för {d}: {e}")

    if not close_map:
        raise RuntimeError("Kunde inte hämta grouped priser från Polygon.")

    log(f"[INFO] Grouped date used: {ok_date} | tickers={len(close_map)}")

    log("[STEP] Bygger BuyNow…")
    df_out, mode = build_buynow(df_ec, portval, usdsek, min_price, close_map)

    wb = load_workbook(tpl)
    stamp = f"built_by=v2_alt1 | mode={mode} | grouped_date={ok_date} | utc={dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
    write_buynow_sheet(wb, df_out, stamp)

    out = Path(OUTPUT_FILE)
    tmp = out.with_suffix(".tmp")

    log("[STEP] Skriver Momentum.xlsx…")
    wb.save(tmp)
    if out.exists():
        out.unlink()
    tmp.replace(out)

    log("[OK] Momentum.xlsx uppdaterad — BuyNow.")
    log(f"[OK] Mode={mode} | BuyNow: {', '.join(df_out['Ticker'].astype(str).tolist())}")

if __name__ == "__main__":
    main()
