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

# === Konfig ===
TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()
TARGET_POSITIONS = 10  # hur många lika stora positioner du vill hålla samtidigt


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
    """Hämta USD/SEK från Polygon. Fallback 10.0 om API strular."""
    try:
        r = requests.get(
            "https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
            params={"adjusted":"true","limit":1,"apiKey":POLYGON_API},
            timeout=5
        )
        r.raise_for_status()
        data = r.json()
        res = data.get("results", [])
        if res and res[0].get("c"):
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] polygon misslyckades: {e}")
    return 10.0


def read_portfolio_value(path: Path) -> float:
    """
    Läs 'Portföljvärde' i Parametrar-fliken genom att hitta raden med ordet 'Portföljvärde'
    i kolumn A och ta cellen bredvid (kolumn B). Robust mot headers.
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


def build_buylist(df_ec_raw: pd.DataFrame, portfolio_value: float, usdsek: float) -> pd.DataFrame:
    """
    Tobias Momentum Classic (rensad):
    1. Vi tar EarlyCandidates som du redan genererar.
    2. Vi kastar uppenbart skräp:
       - Pris under SMA200  -> långsiktigt nedtrend, bort.
       - Ret1m < -20%       -> den håller på att falla isär just nu, bort.
       - (valfritt) Price_0 < 1 USD? Låter den vara tills du säger att vi ska kasta pennystocks.
    3. Vi räknar ett RankScore baserat på momentum:
       RankScore = 0.5*Score_MOMO + 0.3*Ret1m + 0.2*Ret3m
       (Score_MOMO väger tyngst, sen senaste månaden, sen 3 månader)
    4. Vi sorterar efter RankScore, tar topp 15.
    5. Markera Top10 = SANT på de första 10.
    6. Qty = lika vikter utifrån ditt portföljvärde.
    """

    df = df_ec_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    required_cols = [
        "Ticker",
        "Price_0",
        "SMA200",
        "Ret1m",
        "Ret3m",
        "Score_MOMO"
    ]
    for col in required_cols:
        if col not in df.columns:
            raise RuntimeError(f"Saknar kolumn {col} i EarlyCandidates")

    # Säkerställ numerik där det behövs
    for c in ["Price_0","SMA200","Ret1m","Ret3m","Score_MOMO"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Rensa ogiltiga rader
    df = df.replace([np.inf,-np.inf], np.nan)
    df = df.dropna(subset=["Ticker","Price_0","SMA200","Ret1m","Ret3m","Score_MOMO"])
    df = df[(df["Price_0"] > 0) & (df["SMA200"] > 0)]

    # 1. Släng skräp som du hatar
    #    a) Under långsiktigt medel (Price_0 < SMA200) -> trash
    #    b) Blöder hårt senaste månaden (Ret1m < -20) -> trash
    clean_mask = (df["Price_0"] >= df["SMA200"]) & (df["Ret1m"] >= -20)
    df = df.loc[clean_mask].copy()

    # Om ALLT försvann (riktig björn), så tar vi till slut ändå allt (dvs vi kör utan filtret),
    # annars hade du fortfarande fått tom lista. Du har sagt att du VILL ha kandidater.
    if df.empty:
        df = df_ec_raw.copy()
        df.columns = [str(c).strip() for c in df.columns]
        for c in ["Price_0","SMA200","Ret1m","Ret3m","Score_MOMO"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.replace([np.inf,-np.inf], np.nan)
        df = df.dropna(subset=["Ticker","Price_0","SMA200","Ret1m","Ret3m","Score_MOMO"])
        df = df[(df["Price_0"] > 0) & (df["SMA200"] > 0)].copy()
        df["Forced"] = True
    else:
        df["Forced"] = False

    # 2. RankScore = momentumstyrka
    df["RankScore"] = (
        0.5 * df["Score_MOMO"] +
        0.3 * df["Ret1m"] +
        0.2 * df["Ret3m"]
    )

    # 3. Sortera och välj topp 15
    df = df.sort_values("RankScore", ascending=False).reset_index(drop=True)
    df["Rank"] = df.index + 1
    df["Top10"] = df["Rank"] <= 10

    # 4. Position sizing / Qty
    per_pos_sek = portfolio_value / TARGET_POSITIONS if portfolio_value > 0 else 0.0
    df["FX"]        = usdsek
    df["Price SEK"] = df["Price_0"] * usdsek

    def calc_qty(row):
        if not row["Top10"]:
            return 0
        if row["Price SEK"] <= 0 or per_pos_sek <= 0:
            return 0
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        return q if q > 0 else 1

    df["Qty"] = [calc_qty(r) for _, r in df.iterrows()]
    df["Position SEK"] = df["Qty"] * df["Price SEK"]

    # Begränsa till top 15
    df = df.head(15).copy()

    # Slutliga kolumner för BuyNow-fliken
    out = df[[
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
        "SMA200",
        "RankScore",
        "Forced"
    ]].copy()

    return out


def write_buynow(wb, df_buy):
    """
    Ersätt/uppdatera BuyNow-fliken, men behåll dess tidigare position
    i flikordningen och rör INGENTING annat.
    """
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

    # kolumnbredder så du slipper ####
    for i in range(1, len(df_buy.columns)+1):
        ws.column_dimensions[get_column_letter(i)].width = 14

    # lägg tillbaka BuyNow där den låg
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

    df_ec_raw = pd.read_excel(tpl, sheet_name="EarlyCandidates")
    df_buy = build_buylist(df_ec_raw, portfolio_value, usdsek)

    wb = load_workbook(tpl)
    write_buynow(wb, df_buy)

    out = Path(OUTPUT_FILE)
    tmp = out.with_suffix(".tmp")
    wb.save(tmp)
    if out.exists():
        out.unlink()
    tmp.replace(out)

    tickers = ", ".join(df_buy["Ticker"].astype(str).tolist())
    log(f"[OK] Momentum.xlsx klar. Kandidater: {tickers}")


if __name__ == "__main__":
    main()
