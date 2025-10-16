import os
import sys
import time
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

TRADES_RENAME_MAP = {
    "Date In":        "DateIn",
    "Ticker":         "Ticker",
    "Qty":            "Qty",
    "Entry (USD)":    "EntryUSD",
    "Stop@entry":     "StopEntry",
    "FX@entry":       "FXEntry",
    "Entry SEK":      "EntrySEK",
    "Fee@entry SEK":  "FeeEntrySEK",
    "Date Out":       "DateOut",
    "Exit (USD)":     "ExitUSD",
    "FX@exit":        "FXExit",
    "Exit SEK":       "ExitSEK",
    "Fee@exit SEK":   "FeeExitSEK",
    "P&L SEK":        "PLSEK",
    "P&L %":          "PLPercent",
}
REQUIRED_MIN = ["Ticker", "DateIn", "Qty", "EntryUSD"]

# =========================
# Hjälpfunktioner
# =========================
def log(msg: str):
    print(msg, flush=True)

def today_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def read_sheet_as_df(path: Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)

def polygon_get(url, params=None, timeout_s=5):
    if not POLYGON_API:
        raise RuntimeError("POLYGON_API_KEY saknas i repository secrets.")
    params = dict(params or {})
    params["apiKey"] = POLYGON_API
    r = requests.get(url, params=params, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def get_usdsek_from_polygon() -> float:
    try:
        data = polygon_get("https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
                           params={"adjusted": "true", "limit": 1}, timeout_s=5)
        res = data.get("results", [])
        if res and res[0].get("c") is not None:
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] Misslyckades hämta USDSEK från Polygon: {e}")
    return 10.00

def last_close_usd_fast(tickers, per_call_timeout=3, total_budget_s=12):
    out = {t: None for t in tickers}
    start = time.time()
    for t in tickers:
        if time.time() - start > total_budget_s:
            break
        try:
            data = polygon_get(f"https://api.polygon.io/v2/aggs/ticker/{t}/prev",
                               params={"adjusted": "true", "limit": 1},
                               timeout_s=per_call_timeout)
            res = data.get("results", [])
            if res and res[0].get("c") is not None:
                out[t] = float(res[0]["c"])
        except Exception:
            out[t] = None
    return out

def backup_template(src_path: Path):
    ensure_dir(BACKUP_DIR)
    base = src_path.stem.replace(" ", "_")
    dst = BACKUP_DIR / f"{base}_{today_stamp()}.xlsx"
    shutil.copy2(src_path, dst)
    log(f"[BACKUP] Sparad: {dst.as_posix()}")

def save_atomic(wb, out_path: Path):
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    wb.save(tmp)
    if out_path.exists():
        out_path.unlink()
    tmp.replace(out_path)

def normalize_trades_headers(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = {}
    for c in df.columns:
        key = str(c).strip()
        new_cols[c] = TRADES_RENAME_MAP.get(key, key)
    return df.rename(columns=new_cols)

def coerce_dates(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    return df

def coerce_numeric(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def header_map(ws):
    return { (ws.cell(row=1, column=ci).value or "").strip(): ci for ci in range(1, ws.max_column+1) }

def find_last_data_row(ws, key_cols):
    """Returnera sista rad som innehåller data i någon av nyckelkolumnerna."""
    maxrow = ws.max_row
    last = 1
    for r in range(2, maxrow+1):
        hit = False
        for ci in key_cols:
            if ci and (ws.cell(row=r, column=ci).value not in (None, "", "False", "FALSKT")):
                hit = True
                break
        if hit:
            last = r
    return last

def reorder_after(wb, sheet_to_move, after_sheet):
    names = wb.sheetnames[:]
    if sheet_to_move not in names or after_sheet not in names:
        return
    names.remove(sheet_to_move)
    idx = names.index(after_sheet) + 1
    names.insert(idx, sheet_to_move)
    wb._sheets = [wb[n] for n in names]

# =========================
# Kärnlogik
# =========================
def main():
    # 1) Mall & backup
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)
    backup_template(tpl)

    # 2) Parametrar + USDSEK
    log("[STEP] Läser Parametrar…")
    portfolio_value = 0.0
    try:
        df_param = read_sheet_as_df(tpl, "Parametrar")
        if not df_param.empty:
            col_b = pd.to_numeric(df_param.iloc[:, 1], errors="coerce").dropna()
            if not col_b.empty:
                portfolio_value = float(col_b.iloc[0])
    except Exception:
        pass

    usdsek = get_usdsek_from_polygon()
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value}")
    log(f"[INFO] USDSEK = {usdsek} (polygon)")

    # 3) Trades -> DataFrame
    log("[STEP] Läser Trades…")
    skip_trades_blocks = False
    try:
        raw = read_sheet_as_df(tpl, "Trades")
        df_trades = normalize_trades_headers(raw.copy())
        df_trades = coerce_dates(df_trades, ["DateIn", "DateOut"])
        df_trades = coerce_numeric(df_trades, [
            "Qty","EntryUSD","StopEntry","FXEntry","EntrySEK","FeeEntrySEK",
            "ExitUSD","FXExit","ExitSEK","FeeExitSEK","PLSEK","PLPercent"
        ])

        # Trimma bort rena skräprader
        df_trades = df_trades[~(
            (df_trades.get("Ticker","").astype(str).str.strip().isin(["", "False", "FALSKT"])) &
            (df_trades.get("DateIn").isna())
        )].copy()

        missing = [c for c in REQUIRED_MIN if c not in df_trades.columns]
        if missing:
            log(f"[WARN] Trades saknar obligatoriska kolumner {missing} — hoppar över Holdings/Realized/Trades-P&L.")
            skip_trades_blocks = True

        if not skip_trades_blocks:
            log("[STEP] Beräknar P&L (totalbelopp) för stängda trades…")
            if "EntrySEK" not in df_trades or df_trades["EntrySEK"].isna().all():
                entry_fx = df_trades.get("FXEntry", pd.Series(usdsek, index=df_trades.index)).fillna(usdsek)
                df_trades["EntrySEK"] = df_trades["EntryUSD"].fillna(0) * entry_fx * df_trades["Qty"].fillna(0)
            if "ExitSEK" not in df_trades or df_trades["ExitSEK"].isna().all():
                fx_exit = df_trades.get("FXExit", pd.Series(usdsek, index=df_trades.index)).fillna(usdsek)
                df_trades["ExitSEK"] = df_trades["ExitUSD"].fillna(0) * fx_exit * df_trades["Qty"].fillna(0)

            fee_entry = df_trades.get("FeeEntrySEK", pd.Series(0.0, index=df_trades.index)).fillna(0.0)
            fee_exit  = df_trades.get("FeeExitSEK",  pd.Series(0.0, index=df_trades.index)).fillna(0.0)

            closed_mask = df_trades["DateOut"].notna() & df_trades["ExitSEK"].notna()
            pl_total = (df_trades["ExitSEK"] - fee_exit) - (df_trades["EntrySEK"] + fee_entry)
            with np.errstate(divide='ignore', invalid='ignore'):
                pl_pct = np.where(df_trades["EntrySEK"] != 0, pl_total / df_trades["EntrySEK"], np.nan)

            df_trades.loc[closed_mask, "PLSEK"] = pl_total[closed_mask]
            df_trades.loc[closed_mask, "PLPercent"] = pl_pct[closed_mask]

    except Exception as e:
        log(f"[WARN] Kunde inte läsa/hantera Trades: {e}")
        skip_trades_blocks = True
        df_trades = pd.DataFrame()

    # 4) Öppna arbetsboken för cellvisa uppdateringar
    wb = load_workbook(tpl)

    # 4a) Trades: skriv P&L + formatering + rensa FALSKT-rader
    if "Trades" in wb.sheetnames and not df_trades.empty:
        wsT = wb["Trades"]
        headers = header_map(wsT)
        col_pl_sek = headers.get("P&L SEK")
        col_pl_pct = headers.get("P&L %")
        col_date_in = headers.get("Date In")
        col_date_out = headers.get("Date Out")
        col_ticker = headers.get("Ticker")

        # Bestäm sista datarad baserat på Date In / Ticker / Qty
        key_cols = [col_ticker or 1, col_date_in or 1]
        last_row = find_last_data_row(wsT, key_cols)

        # Skriv P&L-fält rad 2..last_row
        if col_pl_sek and "PLSEK" in df_trades:
            for i, val in enumerate(df_trades["PLSEK"].fillna(""), start=2):
                if i > last_row: break
                wsT.cell(row=i, column=col_pl_sek, value=float(val) if val != "" else None)
        if col_pl_pct and "PLPercent" in df_trades:
            for i, val in enumerate(df_trades["PLPercent"].fillna(""), start=2):
                if i > last_row: break
                wsT.cell(row=i, column=col_pl_pct, value=float(val) if val != "" else None)

        # Formatering: datum + N/O
        if col_date_in:
            wsT.column_dimensions[get_column_letter(col_date_in)].width = 14
        if col_date_out:
            wsT.column_dimensions[get_column_letter(col_date_out)].width = 14
        if col_pl_sek:
            for r in range(2, last_row+1):
                wsT.cell(row=r, column=col_pl_sek).number_format = "#,##0.00"
        if col_pl_pct:
            for r in range(2, last_row+1):
                wsT.cell(row=r, column=col_pl_pct).number_format = "0.00%"

        # Ta bort (radera) rader under last_row som är FALSKT/False i Date In
        if col_date_in:
            r = last_row + 1
            # säkerhetsgräns så vi inte loopar för mycket
            guard = 0
            while r <= wsT.max_row and guard < 2000:
                v = wsT.cell(row=r, column=col_date_in).value
                if v in ("FALSKT", "False", False):
                    wsT.delete_rows(r, 1)
                    # efter delete stannar vi kvar på samma r för att kontrollera nästa som flyttats upp
                    continue
                guard += 1
                r += 1

    # 4b) Holdings: ersätt datarader med öppna trades (DateOut tom)
    if "Holdings" in wb.sheetnames and not skip_trades_blocks and not df_trades.empty:
        wsH = wb["Holdings"]
        hmap = header_map(wsH)
        col_ticker_h = hmap.get("Ticker")
        col_qty_h    = hmap.get("Qty") or hmap.get("Antal")
        col_entrysek = hmap.get("Entry SEK") or hmap.get("EntrySEK")
        col_marksek  = hmap.get("Market SEK") or hmap.get("Marknad SEK")
        col_plsek_h  = hmap.get("P&L SEK") or hmap.get("P/L SEK")
        col_plpct_h  = hmap.get("P&L %")  or hmap.get("P/L %")

        # Om nödvändiga kolumner finns, bygg om tabellen från öppna trades
        if col_ticker_h and col_entrysek:
            open_mask = df_trades["DateOut"].isna()
            base = df_trades.loc[open_mask, ["Ticker","Qty","EntrySEK","EntryUSD"]].copy()
            base["Ticker"] = base["Ticker"].astype(str).str.strip()
            base = base[base["Ticker"] != ""]
            uniq = base["Ticker"].dropna().unique().tolist()[:60]
            last_map = last_close_usd_fast(uniq, per_call_timeout=3, total_budget_s=12)

            # Rensa alla datarader under header (behåll rubrikerna)
            # hitta sista nuvarande datarad och ta bort allt under rad 2
            current_last = find_last_data_row(wsH, [col_ticker_h])
            if current_last >= 2:
                wsH.delete_rows(2, current_last - 1)

            # Skriv nya rader från rad 2
            r = 2
            for _, row in base.iterrows():
                t = str(row["Ticker"]).strip()
                qty = float(row.get("Qty") or 0)
                entry_total = float(row.get("EntrySEK") or 0.0)
                last_usd = last_map.get(t)
                entry_usd = float(row.get("EntryUSD") or 0.0)
                px_usd = last_usd if last_usd is not None else entry_usd
                market_total = px_usd * usdsek * qty if qty and px_usd else None
                pl_sek = (market_total - entry_total) if (market_total is not None) else None
                pl_pct = (pl_sek / entry_total) if (pl_sek is not None and entry_total) else None

                if col_ticker_h: wsH.cell(row=r, column=col_ticker_h, value=t)
                if col_qty_h:    wsH.cell(row=r, column=col_qty_h, value=qty if qty else None)
                if col_entrysek: wsH.cell(row=r, column=col_entrysek, value=entry_total if entry_total else None)
                if col_marksek:  wsH.cell(row=r, column=col_marksek, value=market_total if market_total else None)
                if col_plsek_h:  wsH.cell(row=r, column=col_plsek_h, value=pl_sek if pl_sek is not None else None)
                if col_plpct_h:  wsH.cell(row=r, column=col_plpct_h, value=pl_pct if pl_pct is not None else None)
                r += 1

            end_r = r - 1
            # Formatera siffror i de kolumner som finns
            if col_marksek:
                for rr in range(2, end_r+1):
                    wsH.cell(row=rr, column=col_marksek).number_format = "#,##0.00"
            if col_plsek_h:
                for rr in range(2, end_r+1):
                    wsH.cell(row=rr, column=col_plsek_h).number_format = "#,##0.00"
            if col_plpct_h:
                for rr in range(2, end_r+1):
                    wsH.cell(row=rr, column=col_plpct_h).number_format = "0.00%"

    # 4c) Realized – bredda datumkolumner
    if "Realized" in wb.sheetnames:
        wsR = wb["Realized"]
        hR = header_map(wsR)
        for key in ("DateIn","Date Out","Date Out","Date In"):
            if key in hR:
                wsR.column_dimensions[get_column_letter(hR[key])].width = 14

    # 5) Flikordning
    try:
        reorder_after(wb, "Trades", "BuyNow")
        reorder_after(wb, "Holdings", "Trades")
    except Exception:
        pass

    # 6) Spara
    log("[STEP] Skriver utdata till Excel…")
    save_atomic(wb, Path(OUTPUT_FILE))
    log("[OK] Momentum.xlsx uppdaterad — Trades P&L fixad, FALSKT-rader raderade, Holdings = öppna trades, övriga flikar orörda.")

if __name__ == "__main__":
    main()
