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
# KONFIGURATION
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"   # mallen i repo
OUTPUT_FILE   = "Momentum.xlsx"            # filen som workflow laddar upp som artifact
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

TARGET_POSITIONS = 10  # lika viktade slotar i portföljen


# =========================
# HJÄLPFUNKTIONER
# =========================
def log(msg):
    print(msg, flush=True)

def today_stamp():
    return dt.datetime.now().strftime("%Y%m%d")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def backup_template(src: Path):
    """Spara en snapshot av mallen innan vi skriver ut en ny Momentum.xlsx"""
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ','_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst.as_posix()}")

def read_df(path: Path, sheet: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet)

def polygon_get(url, params=None, timeout_s=5):
    if not POLYGON_API:
        raise RuntimeError("POLYGON_API_KEY saknas i GitHub Secrets.")
    q = dict(params or {})
    q["apiKey"] = POLYGON_API
    r = requests.get(url, params=q, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def get_usdsek() -> float:
    """
    Hämtar senaste stängning USD/SEK från Polygon. Fallback 10.0 om något går fel.
    """
    try:
        data = polygon_get(
            "https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
            {"adjusted": "true", "limit": 1},
            5
        )
        res = data.get("results", [])
        if res and res[0].get("c") is not None:
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] Kunde inte hämta USDSEK, fallback 10.0 ({e})")
    return 10.0

def header_map(ws):
    return {(ws.cell(1, ci).value or "").strip(): ci for ci in range(1, ws.max_column+1)}

def save_atomic(wb, out_path: Path):
    """
    Skriv workbook säkert.
    """
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    wb.save(tmp)
    if out_path.exists():
        out_path.unlink()
    tmp.replace(out_path)


# =========================
# KÄRNLOGIK — BYGG BUY LIST
# =========================
def build_buylist(df_ec: pd.DataFrame, portfolio_value: float, usdsek: float) -> pd.DataFrame:
    """
    Tar EarlyCandidates och bygger en filtrerad/rankad BuyNow-tabell
    med Qty baserat på portföljstorlek och USD/SEK.
    """

    # ---- 1. Mappa kolumner vi förväntar oss ----
    # Vi utgår ifrån att EarlyCandidates har minst:
    #  Ticker, Price_0 (senaste pris i USD), Score_MOMO,
    #  SMA50, SMA200, Ret1m, Ret3m, Price_1m, Price_3m.
    cols = {str(c).strip(): c for c in df_ec.columns}

    def need(colname):
        if colname not in cols:
            raise RuntimeError(f"EarlyCandidates saknar kolumn '{colname}'")
        return cols[colname]

    # Grundkolumner (obligatoriska)
    ticker_col      = need("Ticker")
    price0_col      = need("Price_0")
    score_col       = need("Score_MOMO")

    # Valfria men vi kräver dem i signalerna idag. Om de saknas kastar vi också,
    # för att slippa konstiga listor.
    sma50_col       = need("SMA50")
    sma200_col      = need("SMA200")
    ret1_col        = need("Ret1m")
    ret3_col        = need("Ret3m")
    p1m_col         = need("Price_1m")
    p3m_col         = need("Price_3m")

    df = pd.DataFrame({
        "Ticker":     df_ec[ticker_col].astype(str),
        "Price_0":    pd.to_numeric(df_ec[price0_col], errors="coerce"),
        "Score_MOMO": pd.to_numeric(df_ec[score_col], errors="coerce"),
        "SMA50":      pd.to_numeric(df_ec[sma50_col], errors="coerce"),
        "SMA200":     pd.to_numeric(df_ec[sma200_col], errors="coerce"),
        "Ret1m":      pd.to_numeric(df_ec[ret1_col], errors="coerce"),
        "Ret3m":      pd.to_numeric(df_ec[ret3_col], errors="coerce"),
        "Price_1m":   pd.to_numeric(df_ec[p1m_col], errors="coerce"),
        "Price_3m":   pd.to_numeric(df_ec[p3m_col], errors="coerce"),
    })

    # Städ: bara rows med vettiga data
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["Ticker", "Price_0", "Score_MOMO", "SMA50", "SMA200", "Ret1m", "Ret3m"])
    df = df[df["Price_0"] > 0]
    df = df[df["SMA50"] > 0]
    df = df[df["SMA200"] > 0]

    # ---- 2. MomentumAccel ----
    # "Hur mycket bättre har sista månaden gått jämfört med 3 månader?"
    df["MomentumAccel"] = df["Ret1m"] - df["Ret3m"]

    # ---- 3. Signalblock ----
    # FreshBreak:
    #  - Priset idag bryter över senaste 1m/3m nivåer
    #  - Ret1m positivt
    df["Sig_FreshBreak"] = (
        (df["Price_0"] > df[["Price_1m", "Price_3m"]].max(axis=1, skipna=True)) &
        (df["Ret1m"] > 0)
    )

    # EarlyTrend:
    #  - Priset över SMA50
    #  - SMA50 håller på att komma ikapp SMA200 (>=95% av SMA200)
    df["Sig_EarlyTrend"] = (
        (df["Price_0"] > df["SMA50"]) &
        (df["SMA50"] >= 0.95 * df["SMA200"])
    )

    # PullbackOK:
    #  - Priset fortfarande över SMA50
    #  - 3m trend (Ret3m) är positiv
    #  - 1m inte blodbad (< -5%) och inte redan full FOMO (> +10%)
    df["Sig_PullbackOK"] = (
        (df["Price_0"] > df["SMA50"]) &
        (df["Ret3m"] > 0) &
        (df["Ret1m"].between(-5, 10))
    )

    # StrongTrend:
    #  - Pris redan över SMA200
    #  - SMA50 ovanför SMA200 (= golden cross/etablerad trend)
    #  - Ret3m > 10% (det rör på sig på riktigt, inte bara sidosväng)
    df["Sig_StrongTrend"] = (
        (df["Price_0"] > df["SMA200"]) &
        (df["SMA50"] > df["SMA200"]) &
        (df["Ret3m"] > 10)
    )

    # Minst en signal måste trigga
    df["HasSignal"] = (
        df["Sig_FreshBreak"] |
        df["Sig_EarlyTrend"] |
        df["Sig_PullbackOK"] |
        df["Sig_StrongTrend"]
    )

    # ---- 4. Hårda filter för att slippa skräp ----
    # vi vill INTE ha:
    # - sådant som sprungit orimligt långt från snitten (paraboliskt/blowoff)
    # - sådant som redan tappat rejält senaste månaden
    too_far_vs50   = df["Price_0"] > (1.5 * df["SMA50"])
    too_far_vs200  = df["Price_0"] > (1.25 * df["SMA200"])
    weak_last_1m   = df["Ret1m"] < -5

    base_mask = df["HasSignal"]
    base_mask &= (~too_far_vs50)
    base_mask &= (~too_far_vs200)
    base_mask &= (~weak_last_1m)

    filtered = df.loc[base_mask].copy()

    # fallback 1 (om allt filtreras bort): ta sånt som åtminstone är över SMA50 och har positiv Ret1m
    if filtered.empty:
        fallback_mask = (
            (df["Price_0"] > df["SMA50"]) &
            (df["Ret1m"] > 0)
        )
        filtered = df.loc[fallback_mask].copy()

    # fallback 2 (om fortfarande tomt): ta allt (marknaden kan vara skit men du måste få en lista)
    if filtered.empty:
        filtered = df.copy()

    # ---- 5. Rankning ----
    # RankScore = 0.5 * MomentumAccel + 0.3 * Ret3m + 0.2 * Score_MOMO
    filtered["RankScore"] = (
        0.5 * filtered["MomentumAccel"] +
        0.3 * filtered["Ret3m"] +
        0.2 * filtered["Score_MOMO"]
    )

    filtered = filtered.sort_values("RankScore", ascending=False).head(15).reset_index(drop=True)
    filtered["Rank"] = filtered.index + 1
    filtered["Top10"] = filtered["Rank"] <= 10

    # ---- 6. Position sizing / Qty ----
    per_pos_sek = portfolio_value / TARGET_POSITIONS if portfolio_value > 0 else 0.0

    filtered["Price USD"] = filtered["Price_0"]
    filtered["FX"]        = usdsek
    filtered["Price SEK"] = filtered["Price USD"] * filtered["FX"]

    def calc_qty(row):
        # bara Top10 ska köpas
        if not row["Top10"]:
            return 0
        # om något är konstigt -> qty 0
        if row["Price SEK"] <= 0 or per_pos_sek <= 0:
            return 0
        # lika viktat belopp
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        # minst 1 om den ska köpas
        return q if q > 0 else 1

    filtered["Qty"] = filtered.apply(calc_qty, axis=1)
    filtered["Position SEK"] = filtered["Qty"] * filtered["Price SEK"]

    # ---- 7. Slutlig tabell för BuyNow-fliken ----
    out_cols = [
        "Rank",
        "Ticker",
        "Top10",
        "Qty",
        "Price USD",
        "FX",
        "Price SEK",
        "Position SEK",
        "Score_MOMO",
        "Ret1m",
        "Ret3m",
        "MomentumAccel",
        "RankScore",
        "Sig_FreshBreak",
        "Sig_EarlyTrend",
        "Sig_PullbackOK",
        "Sig_StrongTrend",
    ]
    out = filtered[out_cols].copy()
    return out


def write_buynow_sheet(wb, df_out: pd.DataFrame):
    """
    Skapar/ersätter fliken BuyNow men låter flikordningen i resten av arbetsboken vara som den är.
    ENDA undantaget: om BuyNow redan finns, tas den bort och läggs tillbaka
    PÅ SAMMA PLATS där den låg.
    """

    # 1. hitta var BuyNow låg tidigare (index i wb._sheets)
    old_index = None
    for i, sh in enumerate(wb.worksheets):
        if sh.title == "BuyNow":
            old_index = i
            break

    # 2. ta bort gammal BuyNow om finns
    if "BuyNow" in wb.sheetnames:
        ws_old = wb["BuyNow"]
        wb.remove(ws_old)

    # 3. skapa ny BuyNow
    ws_new = wb.create_sheet("BuyNow")

    # 4. skriv rubriker
    headers = list(df_out.columns)
    for c, h in enumerate(headers, start=1):
        ws_new.cell(1, c, h)

    # 5. skriv data
    for r_idx, row in enumerate(df_out.itertuples(index=False, name=None), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws_new.cell(r_idx, c_idx, val)

    # 6. formatera kolumner
    hm = header_map(ws_new)

    # valuta/nummer
    for colname in ("Price USD","FX","Price SEK","Position SEK"):
        if colname in hm:
            col = hm[colname]
            for r in range(2, ws_new.max_row+1):
                if colname == "FX":
                    ws_new.cell(r, col).number_format = "0.0000"
                else:
                    ws_new.cell(r, col).number_format = "#,##0.00"

    if "Qty" in hm:
        col = hm["Qty"]
        for r in range(2, ws_new.max_row+1):
            ws_new.cell(r, col).number_format = "0"

    if "RankScore" in hm:
        col = hm["RankScore"]
        for r in range(2, ws_new.max_row+1):
            ws_new.cell(r, col).number_format = "0.00"

    # bredda kolumner så man slipper ####
    for i in range(1, len(headers)+1):
        ws_new.column_dimensions[get_column_letter(i)].width = 14

    # 7. Lägg tillbaka BuyNow där den var innan
    # Om BuyNow inte fanns innan = vi lägger den sist (ingen flytt till första)
    new_order = wb.worksheets[:]
    if old_index is not None:
        # ta ut den nya fliken (sista)
        new_sheet = new_order.pop(-1)
        # stoppa in den nya fliken på gamla indexet
        new_order.insert(old_index, new_sheet)
    wb._sheets = new_order


# =========================
# MAIN
# =========================
def main():
    # 1. Kolla att mallen finns
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)

    # 2. Backup på mallen
    backup_template(tpl)

    # 3. Läs Parametrar!B1 (portföljvärde i SEK)
    portfolio_value = 0.0
    try:
        df_param = read_df(tpl, "Parametrar")
        # cell B1 = rad 0, kolumn 1 i df (eftersom df läses in som tabell)
        col_b = pd.to_numeric(df_param.iloc[:, 1], errors="coerce").dropna()
        if not col_b.empty:
            portfolio_value = float(col_b.iloc[0])
    except Exception:
        pass
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value:.2f}")

    # 4. Läs EarlyCandidates
    try:
        df_ec = read_df(tpl, "EarlyCandidates")
    except Exception as e:
        log(f"[ERROR] Kunde inte läsa EarlyCandidates: {e}")
        sys.exit(1)

    # 5. Ta USD/SEK
    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    # 6. Bygg ny BuyNow-tabell
    buy_df = build_buylist(df_ec, portfolio_value, usdsek)

    # 7. Ladda mallen som workbook
    wb = load_workbook(tpl)

    # 8. Skriv in BuyNow i workbook (utan att möblera om resten)
    write_buynow_sheet(wb, buy_df)

    # 9. Spara till Momentum.xlsx
    save_atomic(wb, Path(OUTPUT_FILE))

    log("[OK] Momentum.xlsx skapad med ny BuyNow (signalbaserad, viktad, utan att flytta flikar).")


if __name__ == "__main__":
    main()
