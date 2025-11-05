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
def resolve_price_usd(df: pd.DataFrame, usdsek: float) -> tuple[pd.Series,str]:
    """
    Försök hitta pris i USD. Om bara SEK-pris finns, konvertera till USD med FX/Polygon.
    Returnerar: (Series med USD-pris, loggbeskrivning)
    """
    # 1) USD-pris kandidater
    usd_price_keys = [
        "pricenow","price","last","lastprice","close","lastclose","latest","latestprice",
        "pricelatest","pricenowusd","priceusd","price_0","prisusd","senaste"
    ]
    col_usd = choose_column(df, usd_price_keys, require_positive=True)
    if col_usd:
        s = pd.to_numeric(df[col_usd], errors="coerce")
        s = s.where(s>0)
        if s.dropna().any():
            return s, f"[INFO] Pris (Universe) = {col_usd} [USD]"

    # 2) SEK-pris + FX
    sek_price_keys = [
        "pricenowsek","priceseK","price_sek","prissek","pris(sek)","pris","senastepris","pristodaysek"
    ]
    fx_keys = [
        "fxnow","fx","usdsek","sekusd","exchangerate","rate","fx@entry","fx@exit"
    ]
    col_sek = choose_column(df, sek_price_keys, require_positive=True)
    if col_sek:
        ssek = pd.to_numeric(df[col_sek], errors="coerce")
        ssek = ssek.where(ssek>0)
        col_fx = choose_column(df, fx_keys, require_positive=True)
        if col_fx:
            fx = pd.to_numeric(df[col_fx], errors="coerce")
            fx = fx.where(fx>0)
            susd = ssek / fx
            return susd, f"[INFO] Pris (Universe) = {col_sek} [SEK] -> USD via {col_fx}"
        else:
            # saknar FX-kolumn, använd polygon-kurs
            susd = ssek / max(usdsek, 1e-9)
            return susd, f"[INFO] Pris (Universe) = {col_sek} [SEK] -> USD via Polygon ({usdsek})"

    # 3) Sista utväg: första vettiga numeriska kolumn
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.dropna().gt(0).any():
            log(f"[WARN] Ingen tydlig pris-kolumn; använder {c} (kan vara fel skala)")
            return s, f"[WARN] Pris (Universe) = {c} [okänd]"
    raise RuntimeError("Kunde inte härleda pris i Universe.")

def build_buylist_from_universe(df_u_raw: pd.DataFrame, portfolio_value: float, usdsek: float, min_price_usd: float) -> pd.DataFrame:
    """
    Momentum från Universe:
      1) Hitta pris i USD (auto; SEK->USD vid behov)
      2) Använd Universe-kolumner för SMA50/SMA200/Ret1m/Ret3m/Score_MOMO (robust namnsök)
      3) Filter: pris >= min_price, pris >= SMA200, Ret1m >= -20
      4) Rank: 0.5*Score_MOMO + 0.3*Ret1m + 0.2*Ret3m
      5) Top 15, markera Top10, Qty utifrån Parametrar!B1
    """
    df = df_u_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Kolumner (robust namnsök)
    sma50_col  = choose_column(df, ["sma50","ma50"])
    sma200_col = choose_column(df, ["sma200","ma200"])
    ret1_col   = choose_column(df, ["ret1m","ret_1m","return1m","m1return","retm1"])
    ret3_col   = choose_column(df, ["ret3m","ret_3m","return3m","m3return","retm3"])
    score_col  = choose_column(df, ["scoremomo","score_momo","momentumscore","momosc","momoscore"])

    needed = {"SMA50": sma50_col, "SMA200": sma200_col, "Ret1m": ret1_col, "Ret3m": ret3_col, "Score_MOMO": score_col}
    missing = [k for k,v in needed.items() if v is None]
    if missing:
        raise RuntimeError(f"Saknar nödvändiga kolumner i Universe: {missing}")

    # Numerik
    for c in [sma50_col, sma200_col, ret1_col, ret3_col, score_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Hitta/derivera USD-pris
    price_usd, price_log = resolve_price_usd(df, usdsek)
    log(price_log)
    df["__price_usd__"] = pd.to_numeric(price_usd, errors="coerce")

    # Rensa
    df = df.replace([np.inf,-np.inf], np.nan)
    df = df.dropna(subset=["Ticker", "__price_usd__", sma200_col, ret1_col, ret3_col, score_col])
    df = df[(df["__price_usd__"] > 0) & (df[sma200_col] > 0)]

    # Filter
    df = df[df["__price_usd__"] >= min_price_usd]
    df = df[df["__price_usd__"] >= df[sma200_col]]
    df = df[df[ret1_col] >= -20]

    if df.empty:
        # Fallback: ta topp på momentumscore ändå (så du får en lista)
        df = df_u_raw.copy()
        for c in [sma50_col, sma200_col, ret1_col, ret3_col, score_col]:
            df[c] = pd.to_numeric(df.get(c), errors="coerce")
        price_usd, price_log = resolve_price_usd(df, usdsek)
        log("[WARN] Fallback aktiverad: Universe gav tom lista efter filter.")
        log(price_log)
        df["__price_usd__"] = pd.to_numeric(price_usd, errors="coerce")
        df = df.replace([np.inf,-np.inf], np.nan)
        df = df.dropna(subset=["Ticker", "__price_usd__", sma200_col, ret1_col, ret3_col, score_col])
        df = df[(df["__price_usd__"] > 0) & (df[sma200_col] > 0)]

    # Rank
    df["RankScore"] = 0.5*df[score_col] + 0.3*df[ret1_col] + 0.2*df[ret3_col]
    df = df.sort_values("RankScore", ascending=False).reset_index(drop=True)

    # Topp & sizing
    df["Rank"]  = df.index + 1
    df["Top10"] = df["Rank"] <= 10
    df = df.head(15).copy()

    per_pos_sek = (portfolio_value / TARGET_POSITIONS) if portfolio_value > 0 else 0.0
    df["FX"] = usdsek
    df["Price SEK"] = df["__price_usd__"] * usdsek

    def qty(row):
        if not row["Top10"]:
            return 0
        if row["Price SEK"] <= 0 or per_pos_sek <= 0:
            return 0
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        return max(q, 1)

    df["Qty"] = [qty(r) for _, r in df.iterrows()]
    df["Position SEK"] = df["Qty"] * df["Price SEK"]

    # Utdata
    out = df[[
        "Rank","Ticker","Top10","Qty",
        "__price_usd__", "FX","Price SEK","Position SEK",
        score_col, ret1_col, ret3_col, sma50_col, sma200_col, "RankScore"
    ]].copy()
    out = out.rename(columns={
        "__price_usd__": "Price_Used",
        score_col: "Score_MOMO",
        ret1_col:  "Ret1m",
        ret3_col:  "Ret3m",
        sma50_col: "SMA50",
        sma200_col:"SMA200"
    })
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

    # Läs Universe
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
