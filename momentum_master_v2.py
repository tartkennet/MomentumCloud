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

TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE = "Momentum.xlsx"
BACKUP_DIR = Path("backups")
POLYGON_API = os.environ.get("POLYGON_API_KEY", "").strip()

TARGET_POSITIONS = 10  # lika vikt per position

def log(msg):
    print(msg, flush=True)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def today_stamp():
    return dt.datetime.now().strftime("%Y%m%d")

def backup_template(src: Path):
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ','_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst}")

def get_usdsek():
    try:
        r = requests.get(
            "https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
            params={"adjusted": "true", "limit": 1, "apiKey": POLYGON_API},
            timeout=5
        )
        r.raise_for_status()
        data = r.json()
        res = data.get("results", [])
        if res and res[0].get("c"):
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] polygon misslyckades: {e}")
    return 10.0  # fallback om polygon dör

def read_portfolio_value(path: Path) -> float:
    """
    Robust läsning av Parametrar!B1 motsvarande 'Portföljvärde'.
    Vi letar upp raden som innehåller 'Portföljvärde' i kol A.
    """
    try:
        df = pd.read_excel(path, sheet_name="Parametrar", header=None)
        mask = df[0].astype(str).str.lower().str.contains("portföljvärde", na=False)
        if mask.any():
            val = pd.to_numeric(df.loc[mask, 1], errors="coerce").dropna()
            if not val.empty:
                return float(val.iloc[0])
    except Exception as e:
        log(f"[WARN] Portföljvärde kunde ej läsas: {e}")
    return 0.0

def build_buylist(df_ec: pd.DataFrame, portfolio_value: float, usdsek: float) -> pd.DataFrame:
    """
    NORMAL-filter (det du efterlyser):
    1. Pris ska ligga i upptrend = över både SMA50 och SMA200
    2. SMA50 ska ligga över SMA200 (lång trend upp)
    3. Ret3m > 5%  (aktien går faktiskt upp senaste kvartalet)
    4. Ret1m > 0%  (den är inte knäckt senaste månaden)
    5. MomentumAccel = Ret1m - Ret3m >= -5  (det får inte se ut som den håller på att dö)
       dvs farten får svalna lite, men inte kollapsa
    -> Detta ska ge dig sunda, levande trender. Inte döda grisar, inte bara explosionsspikar.
    """

    df = df_ec.copy()
    df.columns = [str(c).strip() for c in df.columns]

    needed = ["Ticker","Price_0","SMA50","SMA200","Ret1m","Ret3m","Score_MOMO"]
    for col in needed:
        if col not in df.columns:
            raise RuntimeError(f"Saknar kolumn {col} i EarlyCandidates")

    # gör numeriskt där det går
    for c in ["Price_0","SMA50","SMA200","Ret1m","Ret3m","Score_MOMO"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # rensa orimliga rader
    df = df.replace([np.inf,-np.inf], np.nan)
    df = df.dropna(subset=["Ticker","Price_0","SMA50","SMA200","Ret1m","Ret3m"])
    df = df[(df["Price_0"] > 0) & (df["SMA50"] > 0) & (df["SMA200"] > 0)]

    # definiera MomentumAccel
    df["MomentumAccel"] = df["Ret1m"] - df["Ret3m"]

    # Bygg boolean-flaggor som vi kan visa i arket
    df["TrendOK"] = (
        (df["Price_0"] > df["SMA50"]) &
        (df["Price_0"] > df["SMA200"]) &
        (df["SMA50"]  > df["SMA200"])
    )
    df["QuarterUp"] = df["Ret3m"] > 5        # upp senaste 3m
    df["MonthAlive"] = df["Ret1m"] > 0       # inte total breakdown senaste månaden
    df["AccelNotDead"] = (df["MomentumAccel"] >= -5)

    mask = df["TrendOK"] & df["QuarterUp"] & df["MonthAlive"] & df["AccelNotDead"]

    filtered = df.loc[mask].copy()

    # Om vi fortfarande blir tomma → det är en blodig marknad.
    # Då kör vi en mild fallback: bara TrendOK & QuarterUp.
    if filtered.empty:
        fallback_mask = df["TrendOK"] & df["QuarterUp"]
        filtered = df.loc[fallback_mask].copy()

    # Om det ÄNDÅ är tomt → då är marknaden helt kass, då köper vi inget alls.
    if filtered.empty:
        return pd.DataFrame(columns=[
            "Rank","Ticker","Top10","Qty","Price_0","FX","Price SEK","Position SEK",
            "Score_MOMO","Ret1m","Ret3m","MomentumAccel","RankScore",
            "TrendOK","QuarterUp","MonthAlive","AccelNotDead"
        ])

    # Rankning: vi gillar stabil trend (Ret3m), vi gillar att den lever nu (Ret1m),
    # och vi gillar om den inte håller på att dö (MomentumAccel).
    filtered["RankScore"] = (
        0.5 * filtered["Ret3m"] +
        0.3 * filtered["Ret1m"] +
        0.2 * filtered["MomentumAccel"]
    )

    filtered = filtered.sort_values("RankScore", ascending=False).reset_index(drop=True)
    filtered["Rank"]  = filtered.index + 1
    filtered["Top10"] = filtered["Rank"] <= 10

    per_pos_sek = portfolio_value / TARGET_POSITIONS if portfolio_value > 0 else 0.0
    filtered["FX"]        = usdsek
    filtered["Price SEK"] = filtered["Price_0"] * usdsek

    def size_row(row):
        if not row["Top10"]:
            return 0
        if row["Price SEK"] <= 0 or per_pos_sek <= 0:
            return 0
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        return q if q > 0 else 1

    filtered["Qty"] = [size_row(r) for _, r in filtered.iterrows()]
    filtered["Position SEK"] = filtered["Qty"] * filtered["Price SEK"]

    out_cols = [
        "Rank",
        "Ticker",
        "Top10",
        "Qty",
        "Price_0",
        "FX",
        "Price SEK",
        "Position SEK",
        "Score_MOMO",
        "Ret1m",
        "Ret3m",
        "MomentumAccel",
        "RankScore",
        "TrendOK",
        "QuarterUp",
        "MonthAlive",
        "AccelNotDead",
    ]

    return filtered[out_cols].copy()

def write_buynow(wb, df_buy):
    # Hitta ev. gammal BuyNow och kom ihåg var den låg
    old_index = None
    for i, sh in enumerate(wb.worksheets):
        if sh.title == "BuyNow":
            old_index = i
            wb.remove(sh)
            break

    ws = wb.create_sheet("BuyNow")

    # Skriv headers
    for c, h in enumerate(df_buy.columns, start=1):
        ws.cell(1, c, h)

    # Skriv data (kan vara tomt, det är okej)
    for r_idx, row in enumerate(df_buy.itertuples(index=False), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)

    # Gör kolumnerna lite breda
    for i in range(1, len(df_buy.columns)+1):
        ws.column_dimensions[get_column_letter(i)].width = 14

    # Stoppa tillbaka BuyNow där den låg innan om den fanns
    if old_index is not None:
        order = wb.worksheets[:]
        new_sheet = order.pop(-1)
        order.insert(old_index, new_sheet)
        wb._sheets = order

def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        sys.exit(f"Fel: {tpl} saknas")

    backup_template(tpl)

    portfolio_value = read_portfolio_value(tpl)
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value}")

    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek}")

    df_ec = pd.read_excel(tpl, sheet_name="EarlyCandidates")
    df_buy = build_buylist(df_ec, portfolio_value, usdsek)

    wb = load_workbook(tpl)
    write_buynow(wb, df_buy)

    out = Path(OUTPUT_FILE)
    tmp = out.with_suffix(".tmp")
    wb.save(tmp)
    if out.exists():
        out.unlink()
    tmp.replace(out)

    if df_buy.empty:
        log("[OK] Momentum.xlsx skapad. Marknaden ger inget du borde köpa (fallback testad).")
    else:
        tickers = ", ".join(df_buy["Ticker"].tolist())
        log(f"[OK] Momentum.xlsx skapad. Kandidater: {tickers}")

if __name__ == "__main__":
    main()
