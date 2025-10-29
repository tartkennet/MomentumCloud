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
# Konfiguration
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

# =========================
# Hjälpfunktioner
# =========================
def log(msg): print(msg, flush=True)

def today_stamp(): return dt.datetime.now().strftime("%Y%m%d")

def ensure_dir(p: Path): p.mkdir(parents=True, exist_ok=True)

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
    q = dict(params or {}); q["apiKey"] = POLYGON_API
    r = requests.get(url, params=q, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def get_usdsek() -> float:
    try:
        data = polygon_get("https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
                           {"adjusted":"true","limit":1}, 5)
        res = data.get("results", [])
        if res and res[0].get("c") is not None:
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] USDSEK misslyckades, fallback 10.0 (skäl: {e})")
    return 10.0

def header_map(ws):
    return {(ws.cell(1, ci).value or "").strip(): ci for ci in range(1, ws.max_column+1)}

def write_buynow_sheet(wb, df_out: pd.DataFrame):
    # ersätt BuyNow
    if "BuyNow" in wb.sheetnames:
        wb.remove(wb["BuyNow"])
    ws = wb.create_sheet("BuyNow")
    headers = list(df_out.columns)
    for c, h in enumerate(headers, start=1):
        ws.cell(1, c, h)
    for r_idx, row in enumerate(df_out.itertuples(index=False, name=None), start=2):
        for c_idx, val in enumerate(row, start=1):
            ws.cell(r_idx, c_idx, val)
    # format
    h = header_map(ws)
    for nm in ("FX",):
        if nm in h:
            c = h[nm]
            for r in range(2, ws.max_row+1): ws.cell(r, c).number_format = "0.0000"
    for nm in ("Price USD","Price SEK","Position SEK"):
        if nm in h:
            c = h[nm]
            for r in range(2, ws.max_row+1): ws.cell(r, c).number_format = "#,##0.00"
    if "Qty" in h:
        c = h["Qty"]
        for r in range(2, ws.max_row+1): ws.cell(r, c).number_format = "0"
    for i in range(1, len(headers)+1):
        ws.column_dimensions[get_column_letter(i)].width = 14
    # flytta först
    names = wb.sheetnames[:]
    names.remove("BuyNow"); names.insert(0,"BuyNow")
    wb._sheets = [wb[n] for n in names]

def save_atomic(wb, out_path: Path):
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    wb.save(tmp)
    if out_path.exists(): out_path.unlink()
    tmp.replace(out_path)

# =========================
# Huvudflöde
# =========================
def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}"); sys.exit(1)
    backup_template(tpl)

    # Parametrar
    portfolio_value = 0.0
    try:
        dfp = read_df(tpl, "Parametrar")
        col_b = pd.to_numeric(dfp.iloc[:,1], errors="coerce").dropna()
        if not col_b.empty: portfolio_value = float(col_b.iloc[0])
    except Exception: pass
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value:.2f}")

    # EarlyCandidates
    try:
        ec = read_df(tpl, "EarlyCandidates")
    except Exception as e:
        log(f"[ERROR] Kunde inte läsa EarlyCandidates: {e}"); sys.exit(1)

    cols = {str(c).strip(): c for c in ec.columns}
    need = ["Ticker","Price_0","Score_MOMO"]
    for k in need:
        if k not in cols:
            log(f"[ERROR] EarlyCandidates saknar '{k}'"); sys.exit(1)

    df = ec[[cols["Ticker"], cols["Price_0"], cols["Score_MOMO"]]].copy()
    df.columns = ["Ticker","Price_0","Score_MOMO"]

    # valfria
    has = {name: (name in cols) for name in ["SMA50","SMA200","Ret1m","Ret3m","Price_1m","Price_3m"]}
    for name in ["SMA50","SMA200","Ret1m","Ret3m","Price_1m","Price_3m"]:
        if has[name]:
            df[name] = pd.to_numeric(ec[cols[name]], errors="coerce")
        else:
            df[name] = np.nan

    # städa
    df["Price_0"]    = pd.to_numeric(df["Price_0"], errors="coerce")
    df["Score_MOMO"] = pd.to_numeric(df["Score_MOMO"], errors="coerce")
    df = df.replace([np.inf,-np.inf], np.nan).dropna(subset=["Ticker","Price_0","Score_MOMO"])
    df = df[df["Price_0"] > 0]

    # Acceleration
    df["MomentumAccel"] = np.where(df[["Ret1m","Ret3m"]].notna().all(axis=1),
                                   df["Ret1m"].fillna(0) - df["Ret3m"].fillna(0), 0.0)

    # ---- SIGNALER ----
    fresh_break = (
        (df["Price_0"] > df[["Price_1m","Price_3m"]].max(axis=1, skipna=True)) &
        (df["Ret1m"].fillna(0) > 0)
    )

    early_trend = (
        (df["Price_0"] > df["SMA50"]) &
        (df["SMA50"] >= 0.95 * df["SMA200"])
    )

    pullback_ok = (
        (df["Price_0"] > df["SMA50"]) &
        (df["Ret3m"].fillna(0) > 0) &
        (df["Ret1m"].fillna(0).between(-5, 10))
    )

    df["Sig_FreshBreak"] = fresh_break.fillna(False)
    df["Sig_EarlyTrend"] = early_trend.fillna(False)
    df["Sig_PullbackOK"] = pullback_ok.fillna(False)
    df["HasSignal"] = df[["Sig_FreshBreak","Sig_EarlyTrend","Sig_PullbackOK"]].any(axis=1)

    # ---- Uteslut översträckta / svaga ----
    too_far_50   = (df["Price_0"] > 1.5 * df["SMA50"])
    too_far_200  = (df["Price_0"] > 1.25 * df["SMA200"])
    weak_1m      = (df["Ret1m"] < -5)

    mask = df["HasSignal"]
    if has["SMA50"]:  mask &= ~too_far_50.fillna(False)
    if has["SMA200"]: mask &= ~too_far_200.fillna(False)
    if has["Ret1m"]:  mask &= ~weak_1m.fillna(False)

    filtered = df.loc[mask].copy()
    if filtered.empty:
        log("[WARN] Inga träffar på nya signaler – faller tillbaka till lättare filter (Price_0 > SMA50 & Ret1m>0).")
        fallback = (df["Price_0"] > df["SMA50"]) & (df["Ret1m"].fillna(0) > 0)
        filtered = df.loc[fallback.fillna(False)].copy()
    if filtered.empty:
        log("[WARN] Fallback tom – använder ofiltrerad lista tillfälligt.")
        filtered = df.copy()

    # ---- RANKNING ----
    filtered["RankScore"] = (
        0.5*filtered["MomentumAccel"].fillna(0) +
        0.3*filtered["Ret3m"].fillna(0) +
        0.2*filtered["Score_MOMO"].fillna(0)
    )
    filtered = filtered.sort_values("RankScore", ascending=False).head(15).reset_index(drop=True)
    filtered["Rank"] = filtered.index + 1

    # ---- PRIS/FX & QTY ----
    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek:.5f}")
    target_pos = 10
    per_pos_sek = portfolio_value/target_pos if portfolio_value>0 else 0.0

    filtered["Price USD"] = filtered["Price_0"]
    filtered["FX"] = usdsek
    filtered["Price SEK"] = filtered["Price USD"] * filtered["FX"]
    filtered["Top10"] = filtered["Rank"] <= 10

    def qty(row):
        if not row["Top10"] or row["Price SEK"]<=0 or per_pos_sek<=0: return 0
        q = int(np.floor(per_pos_sek / row["Price SEK"]))
        return q if q>0 else 1

    filtered["Qty"] = filtered.apply(qty, axis=1)
    filtered["Position SEK"] = filtered["Qty"] * filtered["Price SEK"]

    # ---- Output ----
    out = filtered[[
        "Rank","Ticker","Top10","Qty","Price USD","FX","Price SEK","Position SEK",
        "Score_MOMO","Ret1m","Ret3m","MomentumAccel","RankScore",
        "Sig_FreshBreak","Sig_EarlyTrend","Sig_PullbackOK"
    ]].copy()

    # skriv till Excel (enbart BuyNow)
    wb = load_workbook(tpl)
    write_buynow_sheet(wb, out)
    log("[STEP] Skriver utdata till Excel…")
    save_atomic(wb, Path(OUTPUT_FILE))
    log("[OK] BuyNow uppdaterad — signalbaserad filtrering och acceleration.")
    
if __name__ == "__main__":
    main()
