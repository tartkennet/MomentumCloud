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

# =========================
# Konfiguration
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"   # exakt filnamn i repo
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

# Visuella rubriker (som i din fil) -> kanoniska
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

def polygon_get(url, params=None):
    if not POLYGON_API:
        raise RuntimeError("POLYGON_API_KEY saknas i repository secrets.")
    params = dict(params or {})
    params["apiKey"] = POLYGON_API
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def get_usdsek_from_polygon() -> float:
    try:
        data = polygon_get("https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
                           params={"adjusted": "true", "limit": 1})
        res = data.get("results", [])
        if res and res[0].get("c") is not None:
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] Misslyckades hämta USDSEK från Polygon: {e}")
    return 10.00  # robust fallback

def backup_template(src_path: Path):
    ensure_dir(BACKUP_DIR)
    base = src_path.stem.replace(" ", "_")
    dst = BACKUP_DIR / f"{base}_{today_stamp()}.xlsx"
    shutil.copy2(src_path, dst)
    log(f"[BACKUP] Sparad: {dst.as_posix()}")

def load_wb(path: Path):
    return load_workbook(path)

def save_wb(wb, out_path: Path):
    wb.save(out_path)

def write_dataframe_to_sheet(wb, sheet_name, df: pd.DataFrame, header=True, index=False):
    # Skapar/rensar och skriver DataFrame till ett ark
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # Rensa rimlig yta snabbt
        for row in ws["A1:ZZ100000"]:
            for cell in row:
                cell.value = None
    else:
        ws = wb.create_sheet(sheet_name)

    # Rubriker
    r = 1
    c = 1
    if header:
        for col in df.columns:
            ws.cell(row=r, column=c, value=str(col))
            c += 1
        r += 1

    # Data
    for row in df.itertuples(index=index, name=None):
        c = 1
        for val in row:
            ws.cell(row=r, column=c, value=val)
            c += 1
        r += 1

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
            "Qty", "EntryUSD", "StopEntry", "FXEntry", "EntrySEK", "FeeEntrySEK",
            "ExitUSD", "FXExit", "ExitSEK", "FeeExitSEK", "PLSEK", "PLPercent"
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

            qty = df_trades["Qty"].fillna(0)
            fee_entry = df_trades.get("FeeEntrySEK", pd.Series(0.0, index=df_trades.index)).fillna(0.0)
            fee_exit  = df_trades.get("FeeExitSEK",  pd.Series(0.0, index=df_trades.index)).fillna(0.0)

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

    # 5) Holdings & Realized (utan pris-hämtning per ticker!)
    log("[STEP] Bygger Holdings & Realized… (utan marknadspris-hämtning)")
    df_holdings = pd.DataFrame()
    df_realized = pd.DataFrame()
    if not skip_trades_blocks and not df_trades.empty:
        open_mask = df_trades["DateOut"].isna()
        closed_mask = ~open_mask

        if open_mask.any():
            df_holdings = df_trades.loc[open_mask, ["Ticker", "Qty", "EntryUSD", "FXEntry", "EntrySEK"]].copy()
            if not df_holdings.empty:
                # Ingen extern pris-hämtning: använd Entry som proxy för Last
                df_holdings["LastUSD"] = df_holdings["EntryUSD"]
                df_holdings["FXNow"]   = usdsek
                df_holdings["LastSEK"] = (df_holdings["LastUSD"].fillna(0) * usdsek).round(6)

                qty = df_holdings["Qty"].fillna(0)
                entry_fx = df_holdings.get("FXEntry", pd.Series(usdsek, index=df_holdings.index)).fillna(usdsek)
                cost_sek = (df_holdings["EntrySEK"].fillna(df_holdings["EntryUSD"] * entry_fx)) * qty
                mkt_sek  = df_holdings["LastSEK"] * qty

                df_holdings["UPL_SEK"] = mkt_sek - cost_sek
                with np.errstate(divide='ignore', invalid='ignore'):
                    df_holdings["UPL_%"] = np.where(cost_sek != 0, df_holdings["UPL_SEK"] / cost_sek, np.nan)

        if closed_mask.any():
            cols_exist = [c for c in ["DateIn","DateOut","Ticker","Qty","EntrySEK","ExitSEK","PLSEK","PLPercent"] if c in df_trades.columns]
            df_realized = df_trades.loc[closed_mask, cols_exist].copy()

    # 6) Review_KPI
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

    # 8) Skriv tillbaka i mallen och spara
    log("[STEP] Skriver utdata till Excel…")
    wb = load_wb(tpl)

    if not df_trades.empty:
        rev_map = {v: k for k, v in TRADES_RENAME_MAP.items()}
        out_cols = [rev_map.get(c, c) for c in df_trades.columns]
        df_trades_out = df_trades.copy()
        df_trades_out.columns = out_cols
        write_dataframe_to_sheet(wb, "Trades", df_trades_out)

    write_dataframe_to_sheet(wb, "Holdings", df_holdings if not df_holdings.empty else pd.DataFrame(columns=["Ticker","Qty","EntryUSD","FXEntry","EntrySEK","LastUSD","FXNow","LastSEK","UPL_SEK","UPL_%"]))
    write_dataframe_to_sheet(wb, "Realized", df_realized if not df_realized.empty else pd.DataFrame(columns=["DateIn","DateOut","Ticker","Qty","EntrySEK","ExitSEK","PLSEK","PLPercent"]))
    write_dataframe_to_sheet(wb, "Review_KPI", df_kpi)
    write_dataframe_to_sheet(wb, "Review", df_review)
    write_dataframe_to_sheet(wb, "Metrics", df_metrics)

    save_wb(wb, Path(OUTPUT_FILE))
    print("[DEBUG] Save done", flush=True)

    log("[OK] Momentum.xlsx uppdaterad — BuyNow, Trades P&L (N/O), Holdings, Realized, Review_KPI, Review & Metrics.")

if __name__ == "__main__":
    main()
