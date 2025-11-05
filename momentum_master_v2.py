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
    """Leta efter en rad i Parametrar-kalkylbladet vars kol A innehåller label_substr; returnera värdet i kol B."""
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

def normalize_cols(cols):
    """lower + ta bort mellanslag, punkter, understreck."""
    return {c: ''.join(ch for ch in c.lower() if ch.isalnum()) for c in cols}

def choose_price_column(df: pd.DataFrame) -> str:
    """
    Försök hitta 'senaste pris' i EarlyCandidates.
    Stöder många rubriker. Faller tillbaka till 'Price_0' om inget bättre.
    Väljer första som finns OCH har rimliga positiva värden.
    """
    # Kandidatnamn (normaliserade)
    wanted = [
        "pricenow","pricenowusd","price","last","lastprice","close","lastclose",
        "closenow","latest","latestprice","pricelatest","pricenowse","pricenowsek",
        "pricese","priceseK","pris","senaste","price_0"  # sist: fallback
    ]
    norm = normalize_cols(df.columns)
    rev = {v: k for k, v in norm.items()}

    # preferensordning: alla utom price_0 först
    for key in wanted:
        if key in rev:
            col = rev[key]
            s = pd.to_numeric(df[col], errors="coerce")
            if s.dropna().gt(0).any():
                if key != "price_0":
                    log(f"[INFO] Vald pris-kolumn = {col} (auto)")
                    return col

    # Fallback till Price_0 om den finns
    for c in df.columns:
        if c.strip().lower() == "price_0":
            log("[INFO] Vald pris-kolumn = Price_0 (fallback)")
            return c

    # Ingen hittad -> ta första numeriska > 0
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.dropna().gt(0).any():
            log(f"[WARN] Ingen tydlig pris-kolumn hittad, använder {c}")
            return c
    raise RuntimeError("Kunde inte hitta någon användbar pris-kolumn i EarlyCandidates.")

# ======= Kärnlogik =======
def build_buylist(df_ec_raw: pd.DataFrame, portfolio_value: float, usdsek: float, min_price_usd: float) -> pd.DataFrame:
    """
    Tobias Momentum Classic (med auto-pris):
      1) Välj 'senaste pris'-kolumn smart.
      2) Släng uppenbart skräp: under SMA200 eller Ret1m < -20% eller pris < min_price_usd.
      3) Ranka: 0.5*Score_MOMO + 0.3*Ret1m + 0.2*Ret3m.
      4) Topp 15; Top10 = SANT; Qty från Parametrar!B1.
    """
    df = df_ec_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Säkerställ kärnkolumner
    required = ["Ticker","SMA200","Ret1m","Ret3m","Score_MOMO"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Saknar kolumn(er) i EarlyCandidates: {missing}")

    # Numerik
    for c in ["SMA200","Ret1m","Ret3m","Score_MOMO"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.replace([np.inf,-np.inf], np.nan).dropna(subset=["Ticker","SMA200","Ret1m","Ret3m","Score_MOMO"])

    # Hitta pris-kolumn
    price_col = choose_price_column(df)
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
    df = df.dropna(subset=[price_col])
    df = df[df[price_col] > 0].copy()

    # Släng skräp
    df = df[(df[price_col] >= min_price_usd) & (df["SMA200"] > 0)]
    df = df[df[price_col] >= df["SMA200"]]                # över 200-d
    df = df[df["Ret1m"] >= -20]                           # inte fritt fall

    if df.empty:
        # Sista skydd: om allt försvann, använd topp på Score_MOMO ändå (du vill hellre ha något än noll)
        df = df_ec_raw.copy()
        df.columns = [str(c).strip() for c in df.columns]
        for c in ["SMA200","Ret1m","Ret3m","Score_MOMO"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df[price_col] = pd.to_numeric(df.get(price_col, np.nan), errors="coerce")
        df = df.replace([np.inf,-np.inf], np.nan).dropna(subset=["Ticker","SMA200","Ret1m","Ret3m","Score_MOMO", price_col])
        df = df[df[price_col] > 0]
        df["Forced"] = True
        log("[WARN] Fallback aktiverad: marknaden gav tom lista efter filter.")
    else:
        df["Forced"] = False

    # Rankscore: momentum
    df["RankScore"] = 0.5*df["Score_MOMO"] + 0.3*df["Ret1m"] + 0.2*df["Ret3m"]
    df = df.sort_values("RankScore", ascending=False).reset_index(drop=True)

    # Begränsa + flagga Top10
    df["Rank"] = df.index + 1
    df["Top10"] = df["Rank"] <= 10
    df = df.head(15).copy()

    # Sizing
    per_pos_sek = (portfolio_value / TARGET_POSITIONS) if portfolio_value > 0 else 0.0
    df["FX"] = usdsek
    df["Price SEK"] = df[price_col] * usdsek

    def calc_qty(row):
        if not row["Top10"]:
            return 0
        if row["Price SEK"] <= 0 or per_pos_sek <= 0:
            return 0
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        return max(q, 1)

    df["Qty"] = [calc_qty(r) for _, r in df.iterrows()]
    df["Position SEK"] = df["Qty"] * df["Price SEK"]

    # Slutkolumner
    out = df[[
        "Rank","Ticker","Top10","Qty",
        price_col, "FX","Price SEK","Position SEK",
        "Score_MOMO","Ret1m","Ret3m","SMA200","RankScore","Forced"
    ]].copy()
    out = out.rename(columns={price_col: "Price_Used"})

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
    # rubriker
    for c, h in enumerate(df_buy.columns, start=1):
        ws.cell(1, c, h)
    # data
    for r_idx, row in enumerate(df_buy.itertuples(index=False), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)
    # kolumnbredder
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

    portval = read_param_value(tpl, "portföljvärde", default=0.0, numeric=True)
    min_price = read_param_value(tpl, "min pris", default=1.0, numeric=True)  # t.ex. Parametrar!B4
    log(f"[INFO] Portföljvärde(SEK) = {portval}")
    log(f"[INFO] Min pris (USD)    = {min_price}")

    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek}")

    df_ec = pd.read_excel(tpl, sheet_name="EarlyCandidates")
    df_buy = build_buylist(df_ec, portval, usdsek, min_price)

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
