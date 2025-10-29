import os
import sys
import shutil
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# =========================
# Konfiguration
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"   # din mall i repo
OUTPUT_FILE   = "Momentum.xlsx"            # fil som genereras i run
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

# =========================
# Hjälpfunktioner
# =========================
def log(msg): 
    print(msg, flush=True)

def today_stamp(): 
    return dt.datetime.now().strftime("%Y%m%d")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def backup_template(src: Path):
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ','_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst.as_posix()}")

def read_df(path: Path, sheet: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet)

def polygon_get(url, params=None, timeout_s=5):
    if not POLYGON_API:
        raise RuntimeError("POLYGON_API_KEY saknas i repository secrets.")
    q = dict(params or {})
    q["apiKey"] = POLYGON_API
    r = requests.get(url, params=q, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def get_usdsek() -> float:
    try:
        data = polygon_get("https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
                           {"adjusted": "true", "limit": 1}, 5)
        res = data.get("results", [])
        if res and res[0].get("c") is not None:
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] USDSEK misslyckades, fallback 10.0 (skäl: {e})")
    return 10.0

def header_map(ws):
    return {(ws.cell(1, ci).value or "").strip(): ci for ci in range(1, ws.max_column+1)}

def write_buynow_sheet(wb, df_out: pd.DataFrame):
    # Ta bort gammal BuyNow och skapa ny
    if "BuyNow" in wb.sheetnames:
        wb.remove(wb["BuyNow"])
    ws = wb.create_sheet("BuyNow")

    # Skriv rubriker
    headers = list(df_out.columns)
    for c, h in enumerate(headers, start=1):
        ws.cell(1, c, h)

    # Skriv rader
    for r_idx, row in enumerate(df_out.itertuples(index=False, name=None), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)

    # Formatering
    hmap = header_map(ws)
    for nm in ("FX",):
        if nm in hmap:
            col = hmap[nm]
            for r in range(2, ws.max_row+1):
                ws.cell(r, col).number_format = "0.0000"
    for nm in ("Price USD", "Price SEK", "Position SEK"):
        if nm in hmap:
            col = hmap[nm]
            for r in range(2, ws.max_row+1):
                ws.cell(r, col).number_format = "#,##0.00"
    if "Qty" in hmap:
        col = hmap["Qty"]
        for r in range(2, ws.max_row+1):
            ws.cell(r, col).number_format = "0"

    # Kolumnbredder
    for i in range(1, len(headers)+1):
        ws.column_dimensions[get_column_letter(i)].width = 14

def save_atomic(wb, out_path: Path):
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    wb.save(tmp)
    if out_path.exists():
        out_path.unlink()
    tmp.replace(out_path)

# =========================
# Huvudflöde: Bygg förbättrad BuyNow
# =========================
def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)

    backup_template(tpl)

    # --- Läs Parametrar (portföljvärde i B1) ---
    portfolio_value = 0.0
    try:
        dfp = read_df(tpl, "Parametrar")
        col_b = pd.to_numeric(dfp.iloc[:, 1], errors="coerce").dropna()
        if not col_b.empty:
            portfolio_value = float(col_b.iloc[0])
    except Exception:
        pass
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value:.2f}")

    # --- Läs EarlyCandidates ---
    try:
        ec = read_df(tpl, "EarlyCandidates")
    except Exception as e:
        log(f"[ERROR] Kunde inte läsa EarlyCandidates: {e}")
        sys.exit(1)

    # Normalisera kolumnnamn (utan att ändra Excel)
    cols = {str(c).strip(): c for c in ec.columns}
    def col(name): return cols.get(name, name)

    required = ["Ticker", "Price_0", "Score_MOMO"]
    for r in required:
        if r not in cols:
            log(f"[ERROR] EarlyCandidates saknar kolumnen '{r}'.")
            sys.exit(1)

    df = ec[[cols["Ticker"], cols["Price_0"], cols["Score_MOMO"]]].copy()
    df.columns = ["Ticker", "Price_0", "Score_MOMO"]

    # Valfria kolumner
    has_sma50  = "SMA50" in cols
    has_sma200 = "SMA200" in cols
    has_ret1   = "Ret1m" in cols
    has_ret3   = "Ret3m" in cols

    if has_sma50:
        df["SMA50"] = pd.to_numeric(ec[cols["SMA50"]], errors="coerce")
    if has_sma200:
        df["SMA200"] = pd.to_numeric(ec[cols["SMA200"]], errors="coerce")
    if has_ret1:
        df["Ret1m"] = pd.to_numeric(ec[cols["Ret1m"]], errors="coerce")
    else:
        df["Ret1m"] = np.nan
    if has_ret3:
        df["Ret3m"] = pd.to_numeric(ec[cols["Ret3m"]], errors="coerce")
    else:
        df["Ret3m"] = np.nan

    # Numerik
    df["Price_0"]    = pd.to_numeric(df["Price_0"], errors="coerce")
    df["Score_MOMO"] = pd.to_numeric(df["Score_MOMO"], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Ticker", "Price_0", "Score_MOMO"])
    df = df[df["Price_0"] > 0]

    # MomentumAccel = Ret1m - Ret3m (om båda finns, annars 0)
    df["MomentumAccel"] = np.where(df[["Ret1m","Ret3m"]].notna().all(axis=1),
                                   df["Ret1m"].fillna(0) - df["Ret3m"].fillna(0),
                                   0.0)

    # --------- FILTRERING (undvik “för långt sprungna”) ----------
    mask = pd.Series(True, index=df.index)

    # Kräv Price_0 > SMA50 (om finns)
    if has_sma50:
        mask &= (df["Price_0"] > df["SMA50"])
        # Uteslut extremt utsträckt: Price_0 > 1.5 * SMA50
        mask &= (df["Price_0"] <= 1.5 * df["SMA50"])

    # Övre trendbegränsning relativt SMA200 (om finns): Price_0 < 1.2 * SMA200
    if has_sma200:
        mask &= (df["Price_0"] < 1.2 * df["SMA200"])

    # Ret1m ska vara positivt om kolumn finns
    if has_ret1:
        mask &= (df["Ret1m"] > 0)

    filtered = df.loc[mask].copy()
    if filtered.empty:
        log("[WARN] Alla kandidater filtrerades bort — använder ofiltrerad lista tillfälligt.")
        filtered = df.copy()

    # --------- RANKNING ----------
    filtered["RankScore"] = 0.6 * filtered["Score_MOMO"].fillna(0) + 0.4 * filtered["MomentumAccel"].fillna(0)
    filtered = filtered.sort_values("RankScore", ascending=False).head(15).reset_index(drop=True)
    filtered["Rank"] = filtered.index + 1

    # --------- PRIS/VALUTA & QTY ----------
    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    TARGET_POSITIONS = 10  # lika vikt
    target_per_pos_sek = portfolio_value / TARGET_POSITIONS if portfolio_value > 0 else 0.0

    filtered["Price USD"] = filtered["Price_0"]
    filtered["FX"] = usdsek
    filtered["Price SEK"] = filtered["Price USD"] * filtered["FX"]
    filtered["Top10"] = filtered["Rank"] <= 10

    def calc_qty(row):
        if not row["Top10"] or row["Price SEK"] <= 0 or target_per_pos_sek <= 0:
            return 0
        return int(np.floor(target_per_pos_sek / row["Price SEK"])) or 1

    filtered["Qty"] = filtered.apply(calc_qty, axis=1)
    filtered["Position SEK"] = filtered["Qty"] * filtered["Price SEK"]

    out = filtered[[
        "Rank", "Ticker", "Top10", "Qty",
        "Price USD", "FX", "Price SEK", "Position SEK",
        "Score_MOMO", "MomentumAccel", "RankScore"
    ]].copy()

    # --------- Skriv till Excel (bara BuyNow) ----------
    wb = load_workbook(tpl)
    write_buynow_sheet(wb, out)

    # Flytta BuyNow först
    try:
        names = wb.sheetnames[:]
        if "BuyNow" in names:
            names.remove("BuyNow")
            names.insert(0, "BuyNow")
            wb._sheets = [wb[n] for n in names]
    except Exception:
        pass

    # Spara
    log("[STEP] Skriver utdata till Excel…")
    save_atomic(wb, Path(OUTPUT_FILE))
    log("[OK] BuyNow uppdaterad — filtrerad & rankad med acceleration.")
    

if __name__ == "__main__":
    main()
