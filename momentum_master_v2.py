import os
import io
import sys
import json
import time
import shutil
import datetime as dt
from pathlib import Path

import pandas as pd
import numpy as np
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# -----------------------
# Konfiguration
# -----------------------
TEMPLATE_FILE = "Momentum mall fil.xlsx"   # exakt detta filnamn enligt din repo
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

# Kolumnnamn – kanoniska
CANON = {
    "DateIn": "DateIn",
    "Ticker": "Ticker",
    "Qty": "Qty",
    "EntryUSD": "EntryUSD",
    "StopEntry": "StopEntry",
    "FXEntry": "FXEntry",
    "EntrySEK": "EntrySEK",
    "FeeEntrySEK": "FeeEntrySEK",
    "DateOut": "DateOut",
    "ExitUSD": "ExitUSD",
    "FXExit": "FXExit",
    "ExitSEK": "ExitSEK",
    "FeeExitSEK": "FeeExitSEK",
    "PLSEK": "PLSEK",
    "PLPercent": "PLPercent",
}

# Ditt visuella rubriknamn → kanoniskt
TRADES_RENAME_MAP = {
    "Date In": "DateIn",
    "Ticker": "Ticker",
    "Qty": "Qty",
    "Entry (USD)": "EntryUSD",
    "Stop@entry": "StopEntry",
    "FX@entry": "FXEntry",
    "Entry SEK": "EntrySEK",
    "Fee@entry SEK": "FeeEntrySEK",
    "Date Out": "DateOut",
    "Exit (USD)": "ExitUSD",
    "FX@exit": "FXExit",
    "Exit SEK": "ExitSEK",
    "Fee@exit SEK": "FeeExitSEK",
    "P&L SEK": "PLSEK",
    "P&L %": "PLPercent",
}

REQUIRED_MIN = ["Ticker", "DateIn", "Qty", "EntryUSD"]  # minsta krav för att kunna bygga vidare

# -----------------------
# Hjälpfunktioner
# -----------------------
def log(msg):
    print(msg, flush=True)

def today_stamp():
    return dt.datetime.now().strftime("%Y%m%d")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def polygon_get(url, params=None):
    if not POLYGON_API:
        raise RuntimeError("POLYGON_API_KEY saknas i repository secrets.")
    headers = {"Accept": "application/json"}
    params = params or {}
    params["apiKey"] = POLYGON_API
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def get_usdsek_from_polygon():
    # Använder "C:USDSEK" FX agg/prev för senaste stängning
    # Fallback: 10.00 om något går fel (men loggar varning).
    try:
        data = polygon_get("https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev", params={"adjusted": "true", "limit": 1})
        results = data.get("results", [])
        if results:
            c = results[0].get("c")
            if c:
                return float(c)
    except Exception as e:
        log(f"[WARN] Misslyckades hämta USDSEK från Polygon: {e}")
    return 10.00

def polygon_last_close_usd(ticker):
    # Hämtar senaste "prev" close i USD för ett US-ticker
    # Returnerar None om misslyckas
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
        data = polygon_get(url, params={"adjusted":"true", "limit":1})
        res = data.get("results", [])
        if res:
            c = res[0].get("c")
            return float(c) if c is not None else None
    except Exception:
        return None
    return None

def normalize_trades_headers(df: pd.DataFrame) -> pd.DataFrame:
    # Trim + normalisera
    new_cols = {}
    for c in df.columns:
        c2 = str(c).strip()
        c2 = TRADES_RENAME_MAP.get(c2, c2)  # mappa om känt visuellt namn
        new_cols[c] = c2
    df = df.rename(columns=new_cols)
    return df

def coerce_dates(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    return df

def coerce_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def backup_template(src_path: Path):
    ensure_dir(BACKUP_DIR)
    # Byt mellanslag i namnet endast i backupfilens namn
    base = src_path.stem.replace(" ", "_")
    dst = BACKUP_DIR / f"{base}_{today_stamp()}.xlsx"
    shutil.copy2(src_path, dst)
    log(f"[BACKUP] Sparad: {dst.as_posix()}")

def open_workbook_as_writer(src_path: Path):
    # Ladda mall och skriv utdata i samma struktur
    wb = load_workbook(src_path)
    return wb

def save_workbook(wb, out_path: Path):
    wb.save(out_path)

def write_dataframe_to_sheet(wb, sheet_name, df: pd.DataFrame, header=True, index=False):
    import openpyxl
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # Rensa befintligt innehåll
        for row in ws["A1:ZZ100000"]:
            for cell in row:
                cell.value = None
        # Skriv DataFrame
        start_row = 1
        start_col = 1
        if header:
            for j, col in enumerate(df.columns, start=start_col):
                ws.cell(row=start_row, column=j, value=col)
            start_row += 1
        rows_iter = df.itertuples(index=index, name=None)
        for i, row in enumerate(rows_iter, start=start_row):
            for j, val in enumerate(row, start=1):
                ws.cell(row=i, column=j, value=val)
    else:
        # Skapa nytt ark
        ws = wb.create_sheet(sheet_name)
        write_dataframe_to_sheet(wb, sheet_name, df, header=header, index=index)

def read_sheet_as_df(path: Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)

# -----------------------
# Kärnlogik
# -----------------------
def main():
    # 1) Finns mall?
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)

    # 2) Backup
    backup_template(tpl)

    # 3) Hämta parametrar och USD/SEK
    try:
        df_param = read_sheet_as_df(tpl, "Parametrar")
    except Exception:
        df_param = pd.DataFrame()
    # Förväntar Parametrar!B1 har portföljvärde
    portfolio_value = None
    try:
        # robust: hittat första numeriska cell i kol B
        if not df_param.empty:
            candidates = pd.to_numeric(df_param.iloc[:,1], errors="coerce").dropna()
            if not candidates.empty:
                portfolio_value = float(candidates.iloc[0])
    except Exception:
        pass
    if portfolio_value is None:
        portfolio_value = 0.0

    usdsek = get_usdsek_from_polygon()
    log(f"[INFO] Portföljvärde(SEK) = {portfolio_value}")
    log(f"[INFO] USDSEK = {usdsek} (polygon)")

    # 4) Läs Trades och normalisera rubriker
    skip_trades_blocks = False
    df_trades = None
    try:
        df_trades = read_sheet_as_df(tpl, "Trades")
        df_trades = normalize_trades_headers(df_trades)
        # Coerce typer vi bryr oss om
        df_trades = coerce_dates(df_trades, ["DateIn","DateOut"])
        df_trades = coerce_numeric(df_trades, [
            "Qty","EntryUSD","StopEntry","FXEntry","EntrySEK","FeeEntrySEK",
            "ExitUSD","FXExit","ExitSEK","FeeExitSEK","PLSEK"
        ])
        # Kolla minikrav
        missing = [c for c in REQUIRED_MIN if c not in df_trades.columns]
        if missing:
            log(f"[WARN] Trades saknar obligatoriska kolumner {missing} — hoppar över Holdings/Realized/Trades-P&L.")
            skip_trades_blocks = True
        else:
            # Se till att PL-kolumner finns
            if "PLSEK" not in df_trades.columns:
                df_trades["PLSEK"] = np.nan
            if "PLPercent" not in df_trades.columns:
                df_trades["PLPercent"] = np.nan

            # Räkna P&L för stängda trades (DateOut + Exit finns)
            closed_mask = df_trades["DateOut"].notna() & df_trades["ExitUSD"].notna()
            # Om ExitSEK saknas – räkna ut via ExitUSD * FXExit (eller USDSEK om FXExit saknas)
            fxexit = df_trades["FXExit"] if "FXExit" in df_trades.columns else usdsek
            exit_sek_calc = df_trades["ExitUSD"].fillna(0) * (df_trades.get("FXExit", pd.Series(usdsek, index=df_trades.index)).fillna(usdsek))
            entry_sek = df_trades.get("EntrySEK")
            if entry_sek is None or entry_sek.isna().all():
                # försök räkna EntrySEK om saknas: EntryUSD * FXEntry
                entry_sek = df_trades["EntryUSD"].fillna(0) * (df_trades.get("FXEntry", pd.Series(usdsek, index=df_trades.index)).fillna(usdsek))

            qty = df_trades["Qty"].fillna(0)
            fee_entry = df_trades.get("FeeEntrySEK", pd.Series(0.0, index=df_trades.index)).fillna(0.0)
            fee_exit  = df_trades.get("FeeExitSEK",  pd.Series(0.0, index=df_trades.index)).fillna(0.0)

            # Beräkna endast på stängda
            plsek = (exit_sek_calc * qty - fee_exit) - (entry_sek * qty + fee_entry)
            with np.errstate(divide='ignore', invalid='ignore'):
                plpct = np.where(entry_sek*qty != 0, plsek / (entry_sek*qty), np.nan)

            df_trades.loc[closed_mask, "PLSEK"] = plsek.where(closed_mask, np.nan)
            df_trades.loc[closed_mask, "PLPercent"] = plpct.where(closed_mask, np.nan)

    except Exception as e:
        log(f"[WARN] Kunde inte läsa/hantera Trades: {e}")
        skip_trades_blocks = True

    # 5) Bygg Holdings/Realized (om möjligt)
    df_holdings = pd.DataFrame()
    df_realized = pd.DataFrame()
    if not skip_trades_blocks and df_trades is not None and not df_trades.empty:
        # Öppna = DateOut saknas
        open_mask = df_trades["DateOut"].isna() | (df_trades["DateOut"].astype(str) == "NaT")
        closed_mask = ~open_mask

        # Holdings med enkel mark-to-market
        df_holdings = df_trades.loc[open_mask, ["Ticker","Qty","EntryUSD","FXEntry","EntrySEK"]].copy()
        if not df_holdings.empty:
            # Hämta senaste close för varje ticker
            last_prices = {}
            for t in df_holdings["Ticker"].dropna().unique():
                px = polygon_last_close_usd(str(t).strip())
                last_prices[t] = px
                time.sleep(0.2)  # liten paus mot rate limits
            df_holdings["LastUSD"] = df_holdings["Ticker"].map(last_prices)
            df_holdings["FXNow"] = usdsek
            df_holdings["LastSEK"] = (df_holdings["LastUSD"].fillna(df_holdings["EntryUSD"]) * usdsek).round(4)
            cost_sek = (df_holdings["EntrySEK"].fillna(df_holdings["EntryUSD"]*df_holdings["FXEntry"].fillna(usdsek))) * df_holdings["Qty"].fillna(0)
            mkt_sek  = (df_holdings["LastSEK"] * df_holdings["Qty"].fillna(0))
            df_holdings["UPL_SEK"] = (mkt_sek - cost_sek)
            with np.errstate(divide='ignore', invalid='ignore'):
                df_holdings["UPL_%"] = np.where(cost_sek != 0, df_holdings["UPL_SEK"] / cost_sek, np.nan)

        # Realized från stängda
        df_realized = df_trades.loc[closed_mask, ["DateIn","DateOut","Ticker","Qty","EntrySEK","ExitSEK","PLSEK","PLPercent"]].copy()

    # 6) Review_KPI (enkel status)
    df_kpi = pd.DataFrame({
        "Metric": ["PortfolioValueSEK","USDSEK","OpenPositions","ClosedTrades_Today"],
        "Value": [
            float(portfolio_value),
            float(usdsek),
            int(len(df_holdings)) if df_holdings is not None else 0,
            int(len(df_realized[df_realized["DateOut"] == dt.date.today()])) if not df_realized.empty else 0
        ]
    })

    # 7) Review & Metrics (lägg/uppdatera aktuell månad)
    month_str = dt.date.today().strftime("%Y-%m")
    # En mycket enkel “månadens avkastning” från Realized denna månad i förh. till portfölj (placeholder)
    realized_month = 0.0
    if not df_realized.empty:
        mask_m = df_realized["DateOut"].apply(lambda d: isinstance(d, dt.date) and d.strftime("%Y-%m")==month_str)
        realized_month = float(df_realized.loc[mask_m, "PLSEK"].fillna(0).sum())
    month_ret = float(realized_month / portfolio_value) if portfolio_value else 0.0
    df_review = pd.DataFrame({"Month":[month_str],"Portf_%":[month_ret]})
    df_metrics = pd.DataFrame({"Month":[month_str],"Sharpe":[np.nan],"Sortino":[np.nan]})

    # 8) Skriv utdata: utgå från mallen, uppdatera flikar
    wb = open_workbook_as_writer(tpl)

    # Trades: skriv tillbaka uppdaterad (inkl. PL-kolumner)
    if df_trades is not None and not df_trades.empty:
        # För att spegla din vy: skriv tillbaka med dina visuella rubriker
        # Skapa reverse map för att gå tillbaka till visuella namn där det går
        rev_map = {v:k for k,v in TRADES_RENAME_MAP.items()}
        out_cols = []
        for c in df_trades.columns:
            out_cols.append(rev_map.get(c, c))
        df_trades_out = df_trades.copy()
        df_trades_out.columns = out_cols
        write_dataframe_to_sheet(wb, "Trades", df_trades_out)

    # Holdings
    if df_holdings is not None:
        write_dataframe_to_sheet(wb, "Holdings", df_holdings)

    # Realized
    if df_realized is not None:
        write_dataframe_to_sheet(wb, "Realized", df_realized)

    # Review_KPI
    write_dataframe_to_sheet(wb, "Review_KPI", df_kpi)

    # Review (append-stil: skriv enkel tabell – mallen kan ha sin egen layout, men vi lägger en enkel tabell)
    write_dataframe_to_sheet(wb, "Review", df_review)

    # Metrics
    write_dataframe_to_sheet(wb, "Metrics", df_metrics)

    # Spara till OUTPUT_FILE
    save_workbook(wb, Path(OUTPUT_FILE))

    log("[OK] Momentum.xlsx uppdaterad — BuyNow, Trades P&L (N/O), Holdings, Realized, Review_KPI, Review & Metrics.")


if __name__ == "__main__":
    # GitHub Actions kör "set -e" i shell-steget; vi kör bara main()
    main()
