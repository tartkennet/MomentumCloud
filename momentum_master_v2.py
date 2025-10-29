import os
import sys
import shutil
import datetime as dt
from pathlib import Path

import pandas as pd
import numpy as np
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# =========================
# Konfiguration
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"   # din mall i repo
OUTPUT_FILE   = "Momentum.xlsx"            # färdig fil (sparas lokalt i run)
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
    params = dict(params or {})
    params["apiKey"] = POLYGON_API
    r = requests.get(url, params=params, timeout=timeout_s)
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
    # Skriv header
    headers = list(df_out.columns)
    for c, h in enumerate(headers, start=1):
        ws.cell(1, c, h)
    # Skriv rader
    for r_idx, row in enumerate(df_out.itertuples(index=False, name=None), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)
    # Formatering
    hmap = header_map(ws)
    if "FX" in hmap:
        col = hmap["FX"]
        for r in range(2, ws.max_row+1):
            ws.cell(r, col).number_format = "0.0000"
    for name in ("Price USD", "Price SEK", "Position SEK"):
        if name in hmap:
            col = hmap[name]
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
# Huvudflöde
# =========================
def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)

    backup_template(tpl)

    # Läs Parametrar (portföljvärde i B1)
    portfolio_value = 0.0
    try:
        dfp = read_df(tpl, "Parametrar")
        col_b = pd.to_numeric(dfp.iloc[:, 1], errors="coerce").dropna()
        if not col_b.empty:
            portfolio_value = float(col_b.iloc[0])
    except Exception:
        pass
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value:.2f}")

    # Läs EarlyCandidates
    try:
        ec = read_df(tpl, "EarlyCandidates")
    except Exception as e:
        log(f"[ERROR] Kunde inte läsa EarlyCandidates: {e}")
        sys.exit(1)

    # Säkerställ nödvändiga kolumner
    cols = {str(c).strip(): c for c in ec.columns}
    for must in ("Ticker", "Price_0", "Score_MOMO"):
        if must not in cols:
            log(f"[ERROR] EarlyCandidates saknar kolumnen '{must}'.")
            sys.exit(1)
    # Extrahera
    df = ec.rename(columns=cols)[["Ticker", "Price_0", "Score_MOMO"]].copy()
    # Valfritt filter: om SMA50 finns, kräv Price_0 > SMA50
    if "SMA50" in cols:
        df["SMA50"] = pd.to_numeric(ec[cols["SMA50"]], errors="coerce")
        df = df[df["Price_0"] > df["SMA50"]].copy()

    # Numerik
    df["Price_0"] = pd.to_numeric(df["Price_0"], errors="coerce")
    df["Score_MOMO"] = pd.to_numeric(df["Score_MOMO"], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Ticker", "Price_0", "Score_MOMO"])
    df = df[df["Price_0"] > 0]

    if df.empty:
        log("[ERROR] Inga kandidater kvar efter filtrering.")
        sys.exit(1)

    # Ranka och ta Top 15
    df = df.sort_values("Score_MOMO", ascending=False).head(15).reset_index(drop=True)
    df["Rank"] = df.index + 1
    # Hämta USD/SEK
    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    # Beräkna köpdata
    TARGET_POSITIONS = 10  # lika viktade
    target_per_pos_sek = portfolio_value / TARGET_POSITIONS if portfolio_value > 0 else 0.0

    df["Price USD"] = df["Price_0"]
    df["FX"] = usdsek
    df["Price SEK"] = df["Price USD"] * df["FX"]
    df["Top10"] = df["Rank"] <= 10

    # Qty = floor( target_per_pos / PriceSEK ), minst 1 om Top10, annars 0
    def calc_qty(row):
        if not row["Top10"] or row["Price SEK"] <= 0 or target_per_pos_sek <= 0:
            return 0
        return int(np.floor(target_per_pos_sek / row["Price SEK"])) or 1

    df["Qty"] = df.apply(calc_qty, axis=1)
    df["Position SEK"] = df["Qty"] * df["Price SEK"]

    # Bygg BuyNow-output
    out = df[["Rank", "Ticker", "Top10", "Qty", "Price USD", "FX", "Price SEK", "Position SEK", "Score_MOMO"]].copy()

    # Skriv till ny workbook baserat på mallen (andra flikar orörda)
    wb = load_workbook(tpl)
    write_buynow_sheet(wb, out)
    # Flytta BuyNow först (om du vill ha den i början)
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
    log("[OK] BuyNow uppdaterad i Momentum.xlsx — Top15 med Top10-markering och Qty.")
    

if __name__ == "__main__":
    main()
