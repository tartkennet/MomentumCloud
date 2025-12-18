import os, sys, shutil, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# =========================
# KONFIG
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")

POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()
TARGET_POSITIONS = 10

# =========================
def log(msg): 
    print(msg, flush=True)

def today():
    return dt.datetime.now().strftime("%Y%m%d")

def backup_template(src: Path):
    BACKUP_DIR.mkdir(exist_ok=True)
    dst = BACKUP_DIR / f"{src.stem}_{today()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] {dst}")

# =========================
# POLYGON
# =========================
def polygon_prev_close(tickers):
    out = {}
    for t in tickers:
        try:
            url = f"https://api.polygon.io/v2/aggs/ticker/{t}/prev"
            r = requests.get(
                url,
                params={"adjusted":"true","apiKey":POLYGON_API},
                timeout=10
            )
            r.raise_for_status()
            res = r.json().get("results", [])
            if res:
                out[t] = float(res[0]["c"])
        except Exception as e:
            log(f"[WARN] Polygon price fail {t}: {e}")
    return out

def get_usdsek():
    try:
        r = requests.get(
            "https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
            params={"apiKey":POLYGON_API},
            timeout=10
        )
        r.raise_for_status()
        return float(r.json()["results"][0]["c"])
    except:
        return 10.0

# =========================
# BUY NOW BYGGE
# =========================
def build_buynow(df, portval, usdsek, min_price):

    df = df.copy()
    df["Ticker"] = df["Ticker"].astype(str).str.upper()

    # --- Pris (ENDA källan)
    px = polygon_prev_close(df["Ticker"].tolist())
    df["Price_USD"] = df["Ticker"].map(px)
    df = df.dropna(subset=["Price_USD"])
    df = df[df["Price_USD"] >= min_price]

    # --- Säkerställ numerik
    for c in ["Ret1m","Ret3m","Ret6m","SMA50","SMA200"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["Ret1m","Ret3m","Ret6m","SMA50","SMA200"])

    # --- TRENDKRAV (här dog BKKT)
    df = df[
        (df["Price_USD"] > df["SMA200"]) &
        (df["SMA50"] > df["SMA200"]) &
        (df["Ret1m"] > 0)
    ]

    if df.empty:
        log("[WARN] Inga aktier uppfyller momentumkrav")
        return pd.DataFrame()

    # --- Sammansatt momentum
    df["RankScore"] = (
        0.4 * df["Ret1m"] +
        0.4 * df["Ret3m"] +
        0.2 * df["Ret6m"]
    )

    df = df.sort_values("RankScore", ascending=False)
    df = df.head(15).reset_index(drop=True)

    # --- Sizing
    df["Rank"] = df.index + 1
    df["Top10"] = df["Rank"] <= 10
    df["FX"] = usdsek
    df["Price_SEK"] = df["Price_USD"] * usdsek

    per_pos = portval / TARGET_POSITIONS if portval > 0 else 0
    df["Qty"] = df.apply(
        lambda r: int(per_pos // r["Price_SEK"]) if r["Top10"] else 0,
        axis=1
    )
    df["Position_SEK"] = df["Qty"] * df["Price_SEK"]

    return df

# =========================
# EXCEL
# =========================
def write_sheet(wb, name, df):
    if name in wb.sheetnames:
        wb.remove(wb[name])
    ws = wb.create_sheet(name)
    for c, col in enumerate(df.columns, 1):
        ws.cell(1,c,col)
    for r,row in enumerate(df.itertuples(index=False),2):
        for c,val in enumerate(row,1):
            ws.cell(r,c,val)
    for i in range(1,len(df.columns)+1):
        ws.column_dimensions[get_column_letter(i)].width = 14

# =========================
def main():

    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        sys.exit("Mall saknas")

    backup_template(tpl)

    params = pd.read_excel(tpl, sheet_name="Parametrar", header=None)
    portval   = float(params.loc[params[0]=="Portföljvärde",1].values[0])
    min_price = float(params.loc[params[0]=="Min pris (USD)",1].values[0])

    log(f"[INFO] Portföljvärde: {portval}")
    log(f"[INFO] Min pris USD : {min_price}")

    usdsek = get_usdsek()
    log(f"[INFO] USDSEK: {usdsek:.4f}")

    df_ec = pd.read_excel(tpl, sheet_name="EarlyCandidates")

    df_buy = build_buynow(df_ec, portval, usdsek, min_price)

    wb = load_workbook(tpl)
    if not df_buy.empty:
        write_sheet(wb, "BuyNow", df_buy)

    tmp = Path(OUTPUT_FILE).with_suffix(".tmp")
    wb.save(tmp)
    if Path(OUTPUT_FILE).exists():
        Path(OUTPUT_FILE).unlink()
    tmp.replace(OUTPUT_FILE)

    log("[OK] Momentum.xlsx skapad")
    if not df_buy.empty:
        log("[OK] BuyNow: " + ", ".join(df_buy["Ticker"].tolist()))

if __name__ == "__main__":
    main()
