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

# ======= Konfig =======
TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()
TARGET_POSITIONS = 10  # lika vikt per position

# ======= Hjälp =======
def log(msg): print(msg, flush=True)
def ensure_dir(p: Path): p.mkdir(parents=True, exist_ok=True)
def today_stamp(): return dt.datetime.now().strftime("%Y%m%d")

def backup_template(src: Path):
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ','_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst}")

def get_usdsek():
    """Hämta USD/SEK från Polygon (fallback 10.0)."""
    try:
        r = requests.get(
            "https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
            params={"adjusted":"true","limit":1,"apiKey":POLYGON_API},
            timeout=6
        )
        r.raise_for_status()
        data = r.json().get("results", [])
        if data and data[0].get("c"):
            return float(data[0]["c"])
    except Exception as e:
        log(f"[WARN] polygon misslyckades: {e}")
    return 10.0

def read_param_value(path: Path, label_substr: str, default=None, numeric=True):
    """Hitta rad i Parametrar (kol A innehåller label_substr) och returnera värde i kol B."""
    try:
        df = pd.read_excel(path, sheet_name="Parametrar", header=None)
        mask = df[0].astype(str).str.lower().str.contains(label_substr.lower(), na=False)
        if mask.any():
            val = df.loc[mask, 1].iloc[0]
            if numeric:
                v = pd.to_numeric(val, errors="coerce")
                return default if pd.isna(v) else float(v)
            return str(val)
    except Exception as e:
        log(f"[WARN] Parametrar läsning '{label_substr}' misslyckades: {e}")
    return default

def norm_name(s: str) -> str:
    return ''.join(ch for ch in s.lower() if ch.isalnum())

def choose_column(df: pd.DataFrame, candidates: list[str], require_positive: bool = False) -> str|None:
    """Välj första kolumn vars normaliserade namn matchar någon kandidat."""
    norm_map = {c: norm_name(c) for c in df.columns}
    rev = {v: k for k, v in norm_map.items()}
    for key in candidates:
        if key in rev:
            col = rev[key]
            if require_positive:
                s = pd.to_numeric(df[col], errors="coerce")
                if not s.dropna().gt(0).any():
                    continue
            return col
    return None

# ======= Kärnlogik =======
def build_buylist_from_universe(df_u_raw: pd.DataFrame, portfolio_value: float, usdsek: float, min_price_usd: float) -> pd.DataFrame:
    """
    Momentum från Universe:
      1) Auto-välj pris-kolumn (Close/Price/Last/Price now/…)
      2) Använd Universe-kolumner för SMA50/SMA200/Ret1m/Ret3m/Score_MOMO (robust namnsök)
      3) Filter: pris >= min_price, pris >= SMA200, Ret1m >= -20
      4) Rank: 0.5*Score_MOMO + 0.3*Ret1m + 0.2*Ret3m
      5) Top 15, markera Top10, Qty utifrån Parametrar!B1
    """
    df = df_u_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # --- hitta kolumner robust ---
    # pris
    price_candidates = [
        "pricenow","price","last","lastprice","close","lastclose","latest","latestprice",
        "pricelatest","pricenowusd","priceusd","pris","senaste"
    ]
    price_col = choose_column(df, price_candidates, require_positive=True)
    if not price_col:
        # fallback: Price_0 om den finns
        if "Price_0" in df.columns:
            price_col = "Price_0"
            log("[INFO] Pris-kolumn fallback: Price_0")
        else:
            raise RuntimeError("Hittar ingen pris-kolumn i Universe.")

    # SMA50 / SMA200
    sma50_col  = choose_column(df, ["sma50","ma50"])
    sma200_col = choose_column(df, ["sma200","ma200"])
    # Returer
    ret1_col = choose_column(df, ["ret1m","ret_1m","return1m","m1return","retm1"])
    ret3_col = choose_column(df, ["ret3m","ret_3m","return3m","m3return","retm3"])
    # Score_MOMO
    score_col = choose_column(df, ["scoremomo","score_momo","momentumscore","momosc","momoscore"])

    needed = {
        "Pris": price_col, "SMA50": sma50_col, "SMA200": sma200_col,
        "Ret1m": ret1_col, "Ret3m": ret3_col, "Score_MOMO": score_col
    }
    missing = [k for k,v in needed.items() if v is None]
    if missing:
        raise RuntimeError(f"Saknar nödvändiga kolumner i Universe: {missing}")

    # numerik
    for c in [price_col, sma50_col, sma200_col, ret1_col, ret3_col, score_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.replace([np.inf,-np.inf], np.nan)
    df = df.dropna(subset=["Ticker", price_col, sma200_col, ret1_col, ret3_col, score_col])

    # filter
    df = df[(df[price_col] > 0) & (df[sma200_col] > 0)]
    df = df[df[price_col] >= min_price_usd]
    df = df[df[price_col] >= df[sma200_col]]
    df = df[df[ret1_col] >= -20]

    if df.empty:
        # om inget klarar filtret, ta topp på Score ändå (du vill ha en lista hellre än noll)
        df = df_u_raw.copy()
        for c in [price_col, sma50_col, sma200_col, ret1_col, ret3_col, score_col]:
            df[c] = pd.to_numeric(df.get(c), errors="coerce")
        df = df.replace([np.inf,-np.inf], np.nan)
        df = df.dropna(subset=["Ticker", price_col, sma200_col, ret1_col, ret3_col, score_col])
        df = df[(df[price_col] > 0) & (df[sma200_col] > 0)]
        df["Forced"] = True
        log("[WARN] Fallback aktiverad: Universe gav tom lista efter filter.")
    else:
        df["Forced"] = False

    # rank
    df["RankScore"] = 0.5*df[score_col] + 0.3*df[ret1_col] + 0.2*df[ret3_col]
    df = df.sort_values("RankScore", ascending=False).reset_index(drop=True)

    # toppar
    df["Rank"]  = df.index + 1
    df["Top10"] = df["Rank"] <= 10
    df = df.head(15).copy()

    # sizing
    per_pos_sek = (portfolio_value / TARGET_POSITIONS) if portfolio_value > 0 else 0.0
    df["FX"] = usdsek
    df["Price SEK"] = df[price_col] * usdsek

    def qty(row):
        if not row["Top10"]:
            return 0
        if row["Price SEK"] <= 0 or per_pos_sek <= 0:
            return 0
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        return max(q, 1)

    df["Qty"] = [qty(r) for _, r in df.iterrows()]
    df["Position SEK"] = df["Qty"] * df["Price SEK"]

    # utdata
    out = df[[
        "Rank","Ticker","Top10","Qty",
        price_col, "FX","Price SEK","Position SEK",
        score_col, ret1_col, ret3_col, sma50_col, sma200_col, "RankScore","Forced"
    ]].copy()
    out = out.rename(columns={
        price_col: "Price_Used",
        score_col: "Score_MOMO",
        ret1_col:  "Ret1m",
        ret3_col:  "Ret3m",
        sma50_col: "SMA50",
        sma200_col:"SMA200"
    })
    log(f"[INFO] Vald pris-kolumn (Universe) = {price_col}")
    return out

def write_buynow(wb, df_buy):
    """Ersätt BuyNow utan att flytta andra flikar."""
    old_index = None
    for i, sh in enumerate(wb.worksheets):
        if sh.title == "BuyNow":
            old_index = i
            wb.remove(sh)
            break
    ws = wb.create_sheet("BuyNow")
    for c, h in enumerate(df_buy.columns, start=1):
        ws.cell(1, c, h)
    for r_idx, row in enumerate(df_buy.itertuples(index=False), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)
    for i in range(1, len(df_buy.columns)+1):
        ws.column_dimensions[get_column_letter(i)].width = 14
    if old_index is not None:
        order = wb.worksheets[:]
        new_sheet = order.pop(-1)
        order.insert(old_index, new_sheet)
        wb._sheets = order

# ======= Main =======
def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        sys.exit(f"Fel: {tpl} saknas")

    backup_template(tpl)

    portval   = read_param_value(tpl, "portföljvärde", default=0.0, numeric=True)
    min_price = read_param_value(tpl, "min pris", default=1.0, numeric=True)  # Parametrar!B4 t.ex.
    log(f"[INFO] Portföljvärde(SEK) = {portval}")
    log(f"[INFO] Min pris (USD)    = {min_price}")

    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek}")

    # === Läser Universe istället för EarlyCandidates ===
    df_uni = pd.read_excel(tpl, sheet_name="Universe")

    df_buy = build_buylist_from_universe(df_uni, portval, usdsek, min_price)

    wb = load_workbook(tpl)
    write_buynow(wb, df_buy)

    out = Path(OUTPUT_FILE)
    tmp = out.with_suffix(".tmp")
    wb.save(tmp)
    if out.exists(): out.unlink()
    tmp.replace(out)

    tickers = ", ".join(df_buy["Ticker"].astype(str).tolist())
    log(f"[OK] Momentum.xlsx klar. Kandidater: {tickers}")

if __name__ == "__main__":
    main()
