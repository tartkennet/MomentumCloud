import os, sys, shutil, datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


# =========================
# CONFIG
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "").strip()

SECTOR_MAP_FILE = Path("public/data/sector_map.csv")

TARGET_POSITIONS = 10
DEFAULT_MIN_PRICE_USD = 5.0


# =========================
# HELPERS
# =========================
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

def norm_name(s: str) -> str:
    return "".join(ch for ch in str(s).lower().strip() if ch.isalnum())

def choose_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    names = {c: norm_name(c) for c in df.columns}
    rev = {}
    for k, v in names.items():
        if v not in rev:
            rev[v] = k
    for key in candidates:
        if key in rev:
            return rev[key]
    return None

def read_param_value(path: Path, label_substr: str, default=None, numeric=True):
    """
    Robust läsning från Parametrar utan att kräva exakt text.
    Söker i kol A efter label_substr, tar värdet i kol B.
    """
    try:
        df = pd.read_excel(path, sheet_name="Parametrar", header=None)
        colA = df[0].astype(str).str.lower()
        mask = colA.str.contains(str(label_substr).lower(), na=False)
        if mask.any():
            val = df.loc[mask, 1].iloc[0]
            if numeric:
                v = pd.to_numeric(val, errors="coerce")
                return default if pd.isna(v) else float(v)
            return str(val)
    except Exception as e:
        log(f"[WARN] Parametrar läsning '{label_substr}' misslyckades: {e}")
    return default


# =========================
# POLYGON
# =========================
def polygon_prev_trading_day_local() -> str:
    """
    Returnerar YYYY-MM-DD för 'senaste handelsdag' ungefärligt.
    Vi loopar bakåt tills Polygon grouped-endpoint ger resultat.
    """
    # starta på "igår" (UTC) och backa vid behov
    d = dt.datetime.utcnow().date() - dt.timedelta(days=1)
    for _ in range(10):
        yield d.strftime("%Y-%m-%d")
        d = d - dt.timedelta(days=1)

def polygon_grouped_close_map(date_yyyy_mm_dd: str) -> dict[str, float]:
    """
    Hämtar grouped daily data (1 call) och returnerar ticker -> close (USD).
    """
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


# =========================
# SECTOR MERGE + SCORE
# =========================
def merge_sector_map(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if SECTOR_MAP_FILE.exists():
        sm = pd.read_csv(SECTOR_MAP_FILE)
        if "Ticker" not in sm.columns:
            return df
        sm["Ticker"] = sm["Ticker"].astype(str).str.upper()
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
    """
    Alternativ B:
      - StockMomentum = 0.50*Ret1m + 0.30*Ret3m + 0.20*Ret6m
      - Accel = Ret1m - Ret3m
      - SectorMomentum = median(StockMomentum) per Sector
      - TotalScore = 0.75*StockMomentum + 0.20*z(SectorMomentum) + 0.05*Accel
    """
    df = df.copy()

    for col in ["Ret1m","Ret3m","Ret6m","SMA50","SMA200"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    ret1 = df["Ret1m"].fillna(0.0) if "Ret1m" in df.columns else 0.0
    ret3 = df["Ret3m"].fillna(0.0) if "Ret3m" in df.columns else 0.0
    ret6 = df["Ret6m"].fillna(0.0) if "Ret6m" in df.columns else 0.0

    df["StockMomentum"] = 0.50*ret1 + 0.30*ret3 + 0.20*ret6
    df["Accel"] = ret1 - ret3

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


# =========================
# BUYNOW BUILD
# =========================
def build_buynow(df_ec: pd.DataFrame, portval_sek: float, usdsek: float, min_price_usd: float, close_map: dict[str,float]) -> pd.DataFrame:
    df = df_ec.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Ticker kolumn (robust)
    if "Ticker" not in df.columns:
        alt = choose_column(df, ["ticker","symbol"])
        if alt:
            df = df.rename(columns={alt: "Ticker"})
        else:
            raise RuntimeError("EarlyCandidates saknar Ticker")

    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df = df[df["Ticker"].str.len() > 0]

    # Pris: ONLY Polygon grouped close
    df["Price_USD"] = df["Ticker"].map(close_map)
    df = df.dropna(subset=["Price_USD"])
    df["Price_USD"] = pd.to_numeric(df["Price_USD"], errors="coerce")
    df = df[df["Price_USD"] > 0]
    df = df[df["Price_USD"] >= float(min_price_usd)]

    # Merge sektor
    df = merge_sector_map(df)

    # Säkerställ att returer/SMA finns (om de saknas kan vi inte momentum-ranka på riktigt)
    missing = [c for c in ["Ret1m","Ret3m","Ret6m","SMA50","SMA200"] if c not in df.columns]
    if missing:
        raise RuntimeError(f"Saknar kolumner i EarlyCandidates: {missing}. EarlyCandidates måste innehålla dessa för momentum.")

    df = compute_scores(df)

    # Trend- & momentumfilter (här dör “döda momentum”)
    before = len(df)

    # Pris över SMA200 och SMA50 > SMA200 (stark trend)
    df = df.dropna(subset=["SMA50","SMA200"])
    df = df[(df["SMA200"] > 0) & (df["Price_USD"] >= df["SMA200"]) & (df["SMA50"] > df["SMA200"])]

    # Ret3m positiv
    df = df[df["Ret3m"] > 0]

    # Acceleration: Ret1m > Ret3m (alt 1)
    df = df[df["Ret1m"] > df["Ret3m"]]

    log(f"[INFO] Filter: trend+momentum | {before} -> {len(df)} rader")

    # Om allt blir tomt: relaxa EN gång (behåll ändå momentumdisciplin)
    if df.empty:
        log("[WARN] Tomt efter strikt filter. Relaxar endast Accel (Ret1m > Ret3m) och försöker igen.")
        df = compute_scores(merge_sector_map(df_ec.copy()))
        df.columns = [str(c).strip() for c in df.columns]
        if "Ticker" not in df.columns:
            alt = choose_column(df, ["ticker","symbol"])
            if alt:
                df = df.rename(columns={alt: "Ticker"})
        df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
        df["Price_USD"] = df["Ticker"].map(close_map)
        df = df.dropna(subset=["Price_USD"])
        df["Price_USD"] = pd.to_numeric(df["Price_USD"], errors="coerce")
        df = df[(df["Price_USD"] > 0) & (df["Price_USD"] >= float(min_price_usd))]
        df = merge_sector_map(df)
        for col in ["Ret1m","Ret3m","Ret6m","SMA50","SMA200"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = compute_scores(df)
        df = df.dropna(subset=["SMA50","SMA200"])
        df = df[(df["SMA200"] > 0) & (df["Price_USD"] >= df["SMA200"]) & (df["SMA50"] > df["SMA200"])]
        df = df[df["Ret3m"] > 0]

    if df.empty:
        raise RuntimeError("Inga kandidater efter filter. Kontrollera EarlyCandidates (Ret/SMA) och min pris.")

    # Sort: only TotalScore
    df = df.sort_values("TotalScore", ascending=False).reset_index(drop=True)
    df["Rank"] = df.index + 1
    df["Top10"] = df["Rank"] <= 10
    df = df.head(15).copy()

    # Sizing
    df["FX"] = float(usdsek)
    df["Price_SEK"] = df["Price_USD"] * float(usdsek)

    per_pos = (float(portval_sek) / TARGET_POSITIONS) if portval_sek and portval_sek > 0 else 0.0
    def qty(price_sek: float, top10: bool) -> int:
        if not top10:
            return 0
        if price_sek <= 0 or per_pos <= 0:
            return 0
        q = int(np.floor(per_pos / price_sek))
        return max(q, 1)

    df["Qty"] = [qty(p, t) for p, t in zip(df["Price_SEK"], df["Top10"])]
    df["Position_SEK"] = df["Qty"] * df["Price_SEK"]

    # Output columns (debug-friendly)
    cols = [
        "Rank","Ticker","Top10","Qty",
        "Price_USD","FX","Price_SEK","Position_SEK",
        "Sector","Industry",
        "Ret1m","Ret3m","Ret6m","SMA50","SMA200",
        "StockMomentum","SectorMomentum","Accel","TotalScore",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].copy()


# =========================
# EXCEL WRITE
# =========================
def write_buynow_sheet(wb, df_out: pd.DataFrame, stamp: str):
    # remove old BuyNow (keep sheet order position)
    old_index = None
    for i, sh in enumerate(wb.worksheets):
        if sh.title == "BuyNow":
            old_index = i
            wb.remove(sh)
            break

    ws = wb.create_sheet("BuyNow")

    # header
    for c, h in enumerate(df_out.columns, 1):
        ws.cell(1, c, h)

    # rows
    for r_idx, row in enumerate(df_out.itertuples(index=False), 2):
        for c_idx, val in enumerate(row, 1):
            ws.cell(r_idx, c_idx, val)

    # widths
    for i, name in enumerate(df_out.columns, 1):
        w = 14
        ln = str(name).lower()
        if ln == "ticker":
            w = 10
        if ln in ("sector","industry"):
            w = 18
        ws.column_dimensions[get_column_letter(i)].width = w

    # build stamp
    ws["Z1"] = stamp

    # restore order
    if old_index is not None:
        order = wb.worksheets[:]
        new_sheet = order.pop(-1)
        order.insert(old_index, new_sheet)
        wb._sheets = order


# =========================
# MAIN
# =========================
def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        sys.exit(f"Error: Mallen saknas: {TEMPLATE_FILE}")

    backup_template(tpl)

    portval   = read_param_value(tpl, "portföljvärde", default=0.0, numeric=True)
    min_price = read_param_value(tpl, "min pris", default=DEFAULT_MIN_PRICE_USD, numeric=True)

    usdsek = get_usdsek_prev()

    log(f"[INFO] Portföljvärde(SEK) = {portval}")
    log(f"[INFO] Min pris (USD)    = {min_price}")
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    log("[STEP] Läser EarlyCandidates…")
    df_ec = pd.read_excel(tpl, sheet_name="EarlyCandidates")

    # Polygon grouped close map (fast + korrekt)
    close_map = {}
    ok_date = None
    log("[STEP] Hämtar Polygon grouped priser…")
    for d in polygon_prev_trading_day_local():
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

    log("[STEP] Bygger BuyNow (Alt B + Accel)…")
    df_out = build_buynow(df_ec, portval, usdsek, min_price, close_map)

    wb = load_workbook(tpl)
    stamp = f"built_by=momentum_v2_B_accel | grouped_date={ok_date} | utc={dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
    write_buynow_sheet(wb, df_out, stamp)

    out = Path(OUTPUT_FILE)
    tmp = out.with_suffix(".tmp")

    log("[STEP] Skriver Momentum.xlsx…")
    wb.save(tmp)
    if out.exists():
        out.unlink()
    tmp.replace(out)

    log("[OK] Momentum.xlsx uppdaterad — BuyNow.")
    log(f"[OK] BuyNow tickers: {', '.join(df_out['Ticker'].astype(str).tolist())}")

if __name__ == "__main__":
    main()
