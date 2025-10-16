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
from openpyxl.styles import PatternFill, Font
from openpyxl.formatting.rule import CellIsRule

# =========================
# Konfiguration
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"   # exakt filnamn i repo
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

# Använd dina faktiska rubriker i Trades och mappa till kanoniska
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
    return 10.00  # robust fallback

def last_close_usd_fast(tickers, per_call_timeout=3, total_budget_s=12):
    """
    Hämtar senaste close för en uppsättning tickers, snabbt och säkert.
    Avbryter om total tid överskrids. Fallback None per ticker.
    """
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
    base = src_path.stem.replace(" ", "_")  # endast backupnamn
    dst = BACKUP_DIR / f"{base}_{today_stamp()}.xlsx"
    shutil.copy2(src_path, dst)
    log(f"[BACKUP] Sparad: {dst.as_posix()}")

def save_atomic(wb, out_path: Path):
    """Spara workbook atomiskt: skriv till tempfil och byt namn."""
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

def write_df_replace_sheet(wb, sheet_name, df: pd.DataFrame, header=True, index=False):
    """Ta bort arket om det finns, skapa nytt, skriv df."""
    if sheet_name in wb.sheetnames:
        ws_old = wb[sheet_name]
        wb.remove(ws_old)
    ws = wb.create_sheet(title=sheet_name)

    r = 1
    if header:
        for c, col in enumerate(df.columns, start=1):
            ws.cell(row=r, column=c, value=str(col))
        r += 1
    for row in df.itertuples(index=index, name=None):
        for c, val in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=val)
        r += 1
    return wb[sheet_name]

def set_col_width(ws, col_letter, width):
    ws.column_dimensions[col_letter].width = width

def number_format_range(ws, col_letter, start_row, end_row, fmt):
    for r in range(start_row, end_row + 1):
        cell = ws[f"{col_letter}{r}"]
        cell.number_format = fmt

def apply_posneg_colors(ws, col_letter, start_row, end_row):
    """Grönt för >0, rött för <0."""
    green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    red   = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    ws.conditional_formatting.add(f"{col_letter}{start_row}:{col_letter}{end_row}",
                                  CellIsRule(operator='greaterThan', formula=['0'], fill=green))
    ws.conditional_formatting.add(f"{col_letter}{start_row}:{col_letter}{end_row}",
                                  CellIsRule(operator='lessThan', formula=['0'], fill=red))

def reorder_after(wb, sheet_to_move, after_sheet):
    """Flytta arket 'sheet_to_move' så det hamnar direkt efter 'after_sheet'."""
    # bevara övrig ordning
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
    # 1) Mall
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)

    # 2) Backup
    backup_template(tpl)

    # 3) Parametrar + USD/SEK
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

    # 4) Trades
    log("[STEP] Läser Trades…")
    skip_trades_blocks = False
    df_trades = pd.DataFrame()
    try:
        raw = read_sheet_as_df(tpl, "Trades")
        df_trades = normalize_trades_headers(raw.copy())

        df_trades = coerce_dates(df_trades, ["DateIn", "DateOut"])
        df_trades = coerce_numeric(df_trades, [
            "Qty","EntryUSD","StopEntry","FXEntry","EntrySEK","FeeEntrySEK",
            "ExitUSD","FXExit","ExitSEK","FeeExitSEK","PLSEK","PLPercent"
        ])

        missing = [c for c in REQUIRED_MIN if c not in df_trades.columns]
        if missing:
            log(f"[WARN] Trades saknar obligatoriska kolumner {missing} — hoppar över Holdings/Realized/Trades-P&L.")
            skip_trades_blocks = True

        if "PLSEK" not in df_trades.columns:
            df_trades["PLSEK"] = np.nan
        if "PLPercent" not in df_trades.columns:
            df_trades["PLPercent"] = np.nan

        if not skip_trades_blocks:
            log("[STEP] Beräknar P&L för stängda trades…")
            closed_mask = df_trades["DateOut"].notna() & df_trades["ExitUSD"].notna()

            fx_exit_series = df_trades.get("FXExit", pd.Series(usdsek, index=df_trades.index)).fillna(usdsek)
            exit_sek_calc = df_trades["ExitUSD"].fillna(0) * fx_exit_series

            entry_sek_series = df_trades.get("EntrySEK")
            if entry_sek_series is None or (isinstance(entry_sek_series, pd.Series) and entry_sek_series.isna().all()):
                fx_entry_series = df_trades.get("FXEntry", pd.Series(usdsek, index=df_trades.index)).fillna(usdsek)
                entry_sek_series = df_trades["EntryUSD"].fillna(0) * fx_entry_series

            qty        = df_trades["Qty"].fillna(0)
            fee_entry  = df_trades.get("FeeEntrySEK", pd.Series(0.0, index=df_trades.index)).fillna(0.0)
            fee_exit   = df_trades.get("FeeExitSEK",  pd.Series(0.0, index=df_trades.index)).fillna(0.0)

            denom = (entry_sek_series * qty)
            plsek_series = (exit_sek_calc * qty - fee_exit) - (denom + fee_entry)
            with np.errstate(divide='ignore', invalid='ignore'):
                plpct_vals = np.where(denom != 0, plsek_series / denom, np.nan)
            plpct_series = pd.Series(plpct_vals, index=df_trades.index)

            df_trades.loc[closed_mask, "PLSEK"] = plsek_series[closed_mask]
            df_trades.loc[closed_mask, "PLPercent"] = plpct_series[closed_mask]

    except Exception as e:
        log(f"[WARN] Kunde inte läsa/hantera Trades: {e}")
        skip_trades_blocks = True

    # 5) Holdings & Realized
    log("[STEP] Bygger Holdings & Realized…")
    df_holdings = pd.DataFrame(columns=["Ticker","Qty","Entry SEK","Market SEK","P&L SEK","P&L %"])
    df_realized = pd.DataFrame()

    if not skip_trades_blocks and not df_trades.empty:
        open_mask = df_trades["DateOut"].isna()
        closed_mask = ~open_mask

        # HOLDINGS
        if open_mask.any():
            base = df_trades.loc[open_mask, ["Ticker","Qty","EntryUSD","FXEntry","EntrySEK"]].copy()
            base["Ticker"] = base["Ticker"].astype(str).str.strip()
            uniq = base["Ticker"].dropna().unique().tolist()[:40]  # begränsa batch
            last_map = last_close_usd_fast(uniq, per_call_timeout=3, total_budget_s=12)
            # Market SEK = (last_close_usd eller EntryUSD) * USDSEK
            last_usd = base["Ticker"].map(last_map)
            base["Market SEK"] = (pd.Series(last_usd, index=base.index).fillna(base["EntryUSD"]) * usdsek)
            entry_fx = base.get("FXEntry").fillna(usdsek)
            entry_sek = base["EntrySEK"].where(base["EntrySEK"].notna(), base["EntryUSD"] * entry_fx)
            cost = entry_sek * base["Qty"].fillna(0)
            mkt  = base["Market SEK"] * base["Qty"].fillna(0)
            upl  = mkt - cost
            with np.errstate(divide='ignore', invalid='ignore'):
                upl_pct = np.where(cost != 0, upl / cost, np.nan)
            df_holdings = pd.DataFrame({
                "Ticker":    base["Ticker"],
                "Qty":       base["Qty"],
                "Entry SEK": entry_sek,
                "Market SEK": base["Market SEK"],
                "P&L SEK":   upl,
                "P&L %":     upl_pct,
            })

        # REALIZED
        if closed_mask.any():
            cols_exist = [c for c in ["DateIn","DateOut","Ticker","Qty","EntrySEK","ExitSEK","PLSEK","PLPercent"] if c in df_trades.columns]
            df_realized = df_trades.loc[closed_mask, cols_exist].copy()

    # 6) Review_KPI (enkel)
    log("[STEP] Uppdaterar Review_KPI…")
    closed_today = 0
    if not df_realized.empty and "DateOut" in df_realized.columns:
        today = dt.date.today()
        closed_today = int((pd.to_datetime(df_realized["DateOut"], errors="coerce").dt.date == today).sum())
    df_kpi = pd.DataFrame({
        "Metric": ["PortfolioValueSEK", "USDSEK", "OpenPositions", "ClosedTrades_Today"],
        "Value":  [float(portfolio_value), float(usdsek), int(len(df_holdings)), closed_today]
    })

    # 7) Review & Metrics (förenklad månadsrad)
    log("[STEP] Uppdaterar Review & Metrics…")
    month_str = dt.date.today().strftime("%Y-%m")
    realized_month = 0.0
    if not df_realized.empty and "DateOut" in df_realized.columns and "PLSEK" in df_realized.columns:
        douts = pd.to_datetime(df_realized["DateOut"], errors="coerce").dt.strftime("%Y-%m")
        realized_month = float(df_realized.loc[douts == month_str, "PLSEK"].fillna(0).sum())
    month_ret = float(realized_month / portfolio_value) if portfolio_value else 0.0

    df_review  = pd.DataFrame({"Month": [month_str], "Portf_%": [month_ret]})
    df_metrics = pd.DataFrame({"Month": [month_str], "Sharpe": [np.nan], "Sortino": [np.nan]})

    # 8) Skriv tillbaka i mallen och formatera
    log("[STEP] Skriver utdata till Excel…")
    wb = load_workbook(tpl)

    # --- Trades (behåll dina visuella rubriker) ---
    if not df_trades.empty:
        rev_map = {v: k for k, v in TRADES_RENAME_MAP.items()}
        out_cols = [rev_map.get(c, c) for c in df_trades.columns]
        df_trades_out = df_trades.copy()
        df_trades_out.columns = out_cols
        wsT = write_df_replace_sheet(wb, "Trades", df_trades_out)
        # Datumformat + kolumnbredder
        # anta Date In = kolumn A, Date Out = kolumn I (i din layout)
        set_col_width(wsT, "A", 14)  # Date In
        set_col_width(wsT, "I", 14)  # Date Out
        # antal rader
        nrows = wsT.max_row
        # P&L SEK (kol N), P&L % (kol O) — format
        number_format_range(wsT, "N", 2, nrows, "#,##0.00")
        number_format_range(wsT, "O", 2, nrows, "0.00%")

    # --- Holdings (nya tydliga rubriker) ---
    wsH = write_df_replace_sheet(wb, "Holdings", df_holdings if not df_holdings.empty else
                                 pd.DataFrame(columns=["Ticker","Qty","Entry SEK","Market SEK","P&L SEK","P&L %"]))
    # format + färger + summa-rad
    nrowsH = wsH.max_row
    if nrowsH >= 2:
        # bredd
        set_col_width(wsH, "A", 12)  # Ticker
        set_col_width(wsH, "B", 8)   # Qty
        set_col_width(wsH, "C", 12)  # Entry SEK
        set_col_width(wsH, "D", 12)  # Market SEK
        set_col_width(wsH, "E", 12)  # P&L SEK
        set_col_width(wsH, "F", 10)  # P&L %
        # number formats
        number_format_range(wsH, "B", 2, nrowsH, "0")
        number_format_range(wsH, "C", 2, nrowsH, "#,##0.00")
        number_format_range(wsH, "D", 2, nrowsH, "#,##0.00")
        number_format_range(wsH, "E", 2, nrowsH, "#,##0.00")
        number_format_range(wsH, "F", 2, nrowsH, "0.00%")
        # färger på plus/minus
        apply_posneg_colors(wsH, "E", 2, nrowsH)  # P&L SEK
        apply_posneg_colors(wsH, "F", 2, nrowsH)  # P&L %

        # summa-rad
        total_row = nrowsH + 1
        wsH[f"A{total_row}"].value = "TOTAL"
        wsH[f"A{total_row}"].font = Font(bold=True)
        wsH[f"E{total_row}"].value = f"=SUM(E2:E{nrowsH})"
        wsH[f"F{total_row}"].value = f"=AVERAGE(F2:F{nrowsH})"
        wsH[f"E{total_row}"].number_format = "#,##0.00"
        wsH[f"F{total_row}"].number_format = "0.00%"

    # --- Realized ---
    write_df_replace_sheet(wb, "Realized", df_realized if not df_realized.empty else
                           pd.DataFrame(columns=["DateIn","DateOut","Ticker","Qty","EntrySEK","ExitSEK","PLSEK","PLPercent"]))

    # --- Review_KPI, Review, Metrics ---
    write_df_replace_sheet(wb, "Review_KPI", df_kpi)
    write_df_replace_sheet(wb, "Review", df_review)
    write_df_replace_sheet(wb, "Metrics", df_metrics)

    # --- Flikordning: flytta Trades och Holdings direkt efter BuyNow ---
    try:
        reorder_after(wb, "Trades", "BuyNow")
        reorder_after(wb, "Holdings", "Trades")
    except Exception:
        pass  # om fliknamn saknas hoppar vi bara över

    # Spara atomiskt
    save_atomic(wb, Path(OUTPUT_FILE))
    log("[OK] Momentum.xlsx uppdaterad — BuyNow, Trades P&L (N/O), Holdings, Realized, Review_KPI, Review & Metrics.")

if __name__ == "__main__":
    main()
