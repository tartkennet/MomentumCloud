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
# KONFIG
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"   # din mall i repot
OUTPUT_FILE   = "Momentum.xlsx"            # genererad fil som laddas upp som artifact
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

TARGET_POSITIONS = 10  # hur många simultana innehav du vill vikta lika

# =========================
# HJÄLPMETODER
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
        raise RuntimeError("POLYGON_API_KEY saknas i GitHub Secrets.")
    q = dict(params or {})
    q["apiKey"] = POLYGON_API
    r = requests.get(url, params=q, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def get_usdsek() -> float:
    # Hämtar senaste stängning USD/SEK från Polygon. Faller tillbaka till 10.0 om fel.
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

def write_buynow_sheet(wb, df_out: pd.DataFrame):
    """
    Tar bort ev. gammal BuyNow, skapar en ny BuyNow-flik längst fram,
    skriver tabellen och formaterar kolumner.
    """
    if "BuyNow" in wb.sheetnames:
        wb.remove(wb["BuyNow"])
    ws = wb.create_sheet("BuyNow")

    # skriv rubriker
    headers = list(df_out.columns)
    for c, h in enumerate(headers, start=1):
        ws.cell(1, c, h)

    # skriv data
    for r_idx, row in enumerate(df_out.itertuples(index=False, name=None), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)

    # formatering
    hm = header_map(ws)

    # Valuta/procentformat etc.
    numeric_money_cols = ["Price USD","FX","Price SEK","Position SEK"]
    for colname in numeric_money_cols:
        if colname in hm:
            col = hm[colname]
            for r in range(2, ws.max_row+1):
                if colname == "FX":
                    ws.cell(r, col).number_format = "0.0000"
                else:
                    ws.cell(r, col).number_format = "#,##0.00"

    if "Qty" in hm:
        col = hm["Qty"]
        for r in range(2, ws.max_row+1):
            ws.cell(r, col).number_format = "0"

    if "RankScore" in hm:
        col = hm["RankScore"]
        for r in range(2, ws.max_row+1):
            ws.cell(r, col).number_format = "0.00"

    # bredda alla kolumner lite så att man slipper ####
    for i in range(1, len(headers)+1):
        ws.column_dimensions[get_column_letter(i)].width = 14

    # flytta BuyNow överst i ordningen (flik längst till vänster)
    names = wb.sheetnames[:]
    names.remove("BuyNow")
    names.insert(0, "BuyNow")
    wb._sheets = [wb[n] for n in names]

def save_atomic(wb, out_path: Path):
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    wb.save(tmp)
    if out_path.exists():
        out_path.unlink()
    tmp.replace(out_path)

# =========================
# KÄRNLOGIK FÖR BUY LISTAN
# =========================

def build_buylist(df_ec: pd.DataFrame, portfolio_value: float, usdsek: float) -> pd.DataFrame:
    """
    Tar EarlyCandidates och bygger en filtrerad, rankad lista med kvantitet per aktie.
    """

    # Säkerställ/rename för kolumner vi behöver
    # Vi förväntar oss minst:
    #  - Ticker
    #  - Price_0  (senaste pris i USD)
    #  - Score_MOMO
    # Helst även:
    #  - SMA50
    #  - SMA200
    #  - Ret1m, Ret3m
    #  - Price_1m, Price_3m
    cols = {str(c).strip(): c for c in df_ec.columns}

    required = ["Ticker","Price_0","Score_MOMO"]
    for need in required:
        if need not in cols:
            raise RuntimeError(f"EarlyCandidates saknar kolumn '{need}'")

    df = pd.DataFrame({
        "Ticker":      df_ec[cols["Ticker"]],
        "Price_0":     pd.to_numeric(df_ec[cols["Price_0"]], errors="coerce"),
        "Score_MOMO":  pd.to_numeric(df_ec[cols["Score_MOMO"]], errors="coerce"),
    })

    # valfria kolumner
    def optcol(name, default=np.nan):
        if name in cols:
            return pd.to_numeric(df_ec[cols[name]], errors="coerce")
        else:
            return pd.Series(default, index=df.index, dtype="float64")

    df["SMA50"]    = optcol("SMA50")
    df["SMA200"]   = optcol("SMA200")
    df["Ret1m"]    = optcol("Ret1m")
    df["Ret3m"]    = optcol("Ret3m")
    df["Price_1m"] = optcol("Price_1m")
    df["Price_3m"] = optcol("Price_3m")

    # kasta skräp (saknar pris eller ticker)
    df = df.replace([np.inf,-np.inf], np.nan)
    df = df.dropna(subset=["Ticker","Price_0","Score_MOMO"])
    df = df[df["Price_0"] > 0]

    # MomentumAccel: acceleration på kort sikt
    # tanken: positiv om Ret1m nyligen förbättrats relativt Ret3m
    df["MomentumAccel"] = np.where(
        df[["Ret1m","Ret3m"]].notna().all(axis=1),
        df["Ret1m"].fillna(0) - df["Ret3m"].fillna(0),
        0.0
    )

    # ---------------------------
    # SIGNALER
    # ---------------------------

    # 1) FreshBreak:
    #    Pris idag högre än senaste 1m/3m topp (Price_0 > Price_1m och Price_0 > Price_3m),
    #    och momentum senaste månaden positivt
    fresh_break = (
        (df["Price_0"] > df[["Price_1m","Price_3m"]].max(axis=1, skipna=True)) &
        (df["Ret1m"].fillna(0) > 0)
    )

    # 2) EarlyTrend:
    #    Pris över SMA50.
    #    SMA50 håller på att komma ikapp SMA200 (inte dödtrend):
    #    SMA50 >= 0.95 * SMA200 (alltså nästan ett "golden cross"-läge)
    early_trend = (
        (df["Price_0"] > df["SMA50"]) &
        (df["SMA50"] >= 0.95 * df["SMA200"])
    )

    # 3) PullbackOK:
    #    Pris fortfarande över SMA50 (styrka intakt),
    #    Ret3m positivt (= trend finns),
    #    Ret1m inte har kraschat (<-5%) och inte sprungit hysteriskt (>10%)
    pullback_ok = (
        (df["Price_0"] > df["SMA50"]) &
        (df["Ret3m"].fillna(0) > 0) &
        (df["Ret1m"].fillna(0).between(-5, 10))
    )

    df["Sig_FreshBreak"]  = fresh_break.fillna(False)
    df["Sig_EarlyTrend"]  = early_trend.fillna(False)
    df["Sig_PullbackOK"]  = pullback_ok.fillna(False)

    df["HasSignal"] = (
        df["Sig_FreshBreak"] | df["Sig_EarlyTrend"] | df["Sig_PullbackOK"]
    )

    # ---------------------------
    # FILTRERING
    # ---------------------------

    # Vi vill inte köpa utblåsta namn som har sprungit 200% rakt upp och redan toppat ur.
    # Begränsa: Price_0 får inte vara orimligt långt över snitten.
    too_far_vs50  = df["Price_0"] > (1.5 * df["SMA50"])
    too_far_vs200 = df["Price_0"] > (1.25 * df["SMA200"])

    # Vill inte ha sådant som redan tappat hårt i närtid:
    weak_last_1m = df["Ret1m"] < -5

    mask = df["HasSignal"]

    # Om vi har SMA50, filtrera bort för utsträckt över SMA50
    mask &= (~too_far_vs50.fillna(False))

    # Om vi har SMA200, filtrera bort för långt över lång trend
    mask &= (~too_far_vs200.fillna(False))

    # Om vi har Ret1m, filtrera bort dem som redan tappat mer än -5% sista månaden
    mask &= (~weak_last_1m.fillna(False))

    filtered = df.loc[mask].copy()

    # Om inget klarar signalerna (bear-marknad etc),
    # gör en fallback: minst "pris > SMA50 och Ret1m > 0"
    if filtered.empty:
        fallback_mask = (
            (df["Price_0"] > df["SMA50"]) &
            (df["Ret1m"].fillna(0) > 0)
        )
        filtered = df.loc[fallback_mask.fillna(False)].copy()

    # Om det fortfarande är tomt, ta allt (du måste ändå investera något)
    if filtered.empty:
        filtered = df.copy()

    # ---------------------------
    # RANKNING
    # ---------------------------
    # RankScore = 0.5 * MomentumAccel + 0.3 * Ret3m + 0.2 * Score_MOMO
    filtered["RankScore"] = (
        0.5 * filtered["MomentumAccel"].fillna(0) +
        0.3 * filtered["Ret3m"].fillna(0) +
        0.2 * filtered["Score_MOMO"].fillna(0)
    )

    filtered = filtered.sort_values("RankScore", ascending=False).head(15).reset_index(drop=True)
    filtered["Rank"] = filtered.index + 1
    filtered["Top10"] = filtered["Rank"] <= 10

    # ---------------------------
    # POSITION SIZE
    # ---------------------------
    usdsek = float(usdsek)
    per_pos_sek = portfolio_value / TARGET_POSITIONS if portfolio_value > 0 else 0.0

    filtered["Price USD"] = filtered["Price_0"]
    filtered["FX"]        = usdsek
    filtered["Price SEK"] = filtered["Price USD"] * filtered["FX"]

    def calc_qty(row):
        if not row["Top10"]:
            return 0
        if row["Price SEK"] <= 0 or per_pos_sek <= 0:
            return 0
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        return q if q > 0 else 1

    filtered["Qty"] = filtered.apply(calc_qty, axis=1)
    filtered["Position SEK"] = filtered["Qty"] * filtered["Price SEK"]

    # Slutlig tabell som kommer hamna i BuyNow-fliken
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
    ]
    return filtered[out_cols].copy()

# =========================
# MAIN
# =========================
def main():
    # 1. säkerställ att mallen finns
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)

    # 2. backup på mallen
    backup_template(tpl)

    # 3. hämta portföljvärde
    portfolio_value = 0.0
    try:
        df_param = read_df(tpl, "Parametrar")
        # ta kolumn B första raden (Parametrar!B1)
        col_b = pd.to_numeric(df_param.iloc[:,1], errors="coerce").dropna()
        if not col_b.empty:
            portfolio_value = float(col_b.iloc[0])
    except Exception:
        pass
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value:.2f}")

    # 4. hämta kandidater
    try:
        df_ec = read_df(tpl, "EarlyCandidates")
    except Exception as e:
        log(f"[ERROR] Kunde inte läsa EarlyCandidates: {e}")
        sys.exit(1)

    # 5. USD/SEK
    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    # 6. Bygg buylist
    buy_df = build_buylist(df_ec, portfolio_value, usdsek)

    # 7. skriv tillbaka till en kopia av mallen som Momentum.xlsx
    wb = load_workbook(tpl)
    write_buynow_sheet(wb, buy_df)
    save_atomic(wb, Path(OUTPUT_FILE))

    log("[OK] Klar. BuyNow uppdaterad med signalbaserat urval och viktad Qty.")

if __name__ == "__main__":
    main()
