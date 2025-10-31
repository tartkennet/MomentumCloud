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

TARGET_POSITIONS = 10  # hur många lika stora positioner vi vill hålla

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
    # fallback ifall polygon dör
    return 10.0

def read_portfolio_value(path: Path) -> float:
    """
    Läs 'Portföljvärde' från Parametrar-bladet genom att leta efter raden som heter 'Portföljvärde'
    i kolumn A och ta värdet i kolumn B.
    Fungerar oavsett hur Excel-headern ser ut.
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
    Hård momentum-filtrering (dina krav):
    - Price_0 > SMA50
    - Price_0 > SMA200
    - SMA50 > SMA200  (trend upp, inte sidledes)
    - Ret1m > +10%    (det rör sig NU)
    - MomentumAccel > 0 (farten ökar, inte bromsar)

    Vi plockar bara aktier som uppfyller allt detta.
    Om filtret blir tomt => BuyNow = tom tabell (cashläge).
    """

    df = df_ec.copy()
    df.columns = [str(c).strip() for c in df.columns]

    needed = ["Ticker", "Price_0", "SMA50", "SMA200", "Ret1m", "Ret3m", "Score_MOMO"]
    for col in needed:
        if col not in df.columns:
            raise RuntimeError(f"Saknar kolumn {col} i EarlyCandidates")

    # gör allt numeriskt där det går
    numeric_cols = ["Price_0","SMA50","SMA200","Ret1m","Ret3m","Score_MOMO"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # rensa skräp
    df = df.replace([np.inf,-np.inf], np.nan)
    df = df.dropna(subset=["Ticker","Price_0","SMA50","SMA200","Ret1m","Ret3m"])
    df = df[(df["Price_0"] > 0) & (df["SMA50"] > 0) & (df["SMA200"] > 0)]

    # acceleration = skillnad mellan kort och medellång avkastning
    df["MomentumAccel"] = df["Ret1m"] - df["Ret3m"]

    # tekniska villkor
    df["OverMA"]   = (df["Price_0"] > df["SMA50"]) & (df["Price_0"] > df["SMA200"]) & (df["SMA50"] > df["SMA200"])
    df["Strong1m"] = df["Ret1m"] > 10
    df["AccelOK"]  = df["MomentumAccel"] > 0

    strict_mask = df["OverMA"] & df["Strong1m"] & df["AccelOK"]

    filtered = df.loc[strict_mask].copy()

    # om inget klarar filtret => returnera tom tabell
    if filtered.empty:
        # vi bygger en tom df med samma kolumner som slutoutput,
        # så write_buynow fortfarande skapar fliken utan att krascha.
        cols_out = [
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
            "OverMA",
            "Strong1m",
            "AccelOK",
        ]
        return pd.DataFrame(columns=cols_out)

    # om vi har kandidater: ranka, storleksbestäm
    filtered["RankScore"] = (
        0.6 * filtered["Ret1m"] +
        0.3 * filtered["MomentumAccel"] +
        0.1 * filtered["Score_MOMO"]
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
        "OverMA",
        "Strong1m",
        "AccelOK",
    ]

    return filtered[out_cols].copy()

def write_buynow(wb, df_buy):
    """
    Skapar/ersätter fliken BuyNow men ändrar inte ordningen på andra flikar.
    Om BuyNow fanns tidigare så lägger vi tillbaka den på samma index.
    """
    old_index = None
    for i, sh in enumerate(wb.worksheets):
        if sh.title == "BuyNow":
            old_index = i
            wb.remove(sh)
            break

    ws = wb.create_sheet("BuyNow")

    # headers
    for c, h in enumerate(df_buy.columns, start=1):
        ws.cell(1, c, h)

    # rows (kan vara 0 rader och det är okej)
    for r_idx, row in enumerate(df_buy.itertuples(index=False), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)

    # formatering: kolumnbredder
    for i in range(1, len(df_buy.columns) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 14

    # Lägg tillbaka BuyNow där den låg innan, annars låt den hamna sist
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
        log("[OK] Momentum.xlsx skapad. Ingen aktie klarar hårt momentumfilter → kontantläge.")
    else:
        tickers = ", ".join(df_buy["Ticker"].tolist())
        log(f"[OK] Momentum.xlsx skapad. Kandidater: {tickers}")

if __name__ == "__main__":
    main()
