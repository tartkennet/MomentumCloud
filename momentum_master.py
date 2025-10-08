import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.formatting.rule import Rule
from openpyxl.styles import PatternFill
from openpyxl.worksheet.worksheet import Worksheet
import shutil
from pathlib import Path

# Filer
TEMPLATE = Path("Momentum_template.xlsx")   # Din mall med ALLA flikar (som på bilderna)
OUTPUT   = Path("Momentum.xlsx")            # Filen som byggs/skickas
CACHE    = Path("cache.parquet")            # Full historik (från polygon_fetch_incremental.py)

# Fliknamn
CALC_SHEET = "Calc"
HOLD_SHEET = "Holdings"

# Behövs för SMA200 + 12m-retur
WINDOW_DAYS = 320   # ~15–16 månader

def compute_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """Räkna SMA & returer per ticker på timeserier (begränsa till senaste WINDOW_DAYS)."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["Ticker", "date"])

    # Begränsa storlek per ticker
    df = df.groupby("Ticker", group_keys=False).apply(lambda g: g.tail(WINDOW_DAYS))

    def per_ticker(g):
        g = g.sort_values("date")
        # Rullande (kräv fulla perioder)
        g["SMA50"]  = g["Close"].rolling(50,  min_periods=50).mean()
        g["SMA200"] = g["Close"].rolling(200, min_periods=200).mean()

        # Returer i handelsdagar
        def pct(n): return g["Close"].pct_change(n)
        g["Ret1m"]  = pct(21)
        g["Ret3m"]  = pct(63)
        g["Ret6m"]  = pct(126)
        g["Ret12m"] = pct(252)
        return g

    return df.groupby("Ticker", group_keys=False).apply(per_ticker)

def snapshot_calc(ts: pd.DataFrame) -> pd.DataFrame:
    """
    Gör EN rad per ticker med EXAKTA Calc-kolumnerna:
    Ticker, Price_0, Price_1m, Price_3m, Price_6m, Price_12m,
    SMA50, SMA200, Ret1m, Ret3m, Ret6m, Ret12m, Score_MOMO
    """
    ts = ts.sort_values(["Ticker", "date"])
    rows = []
    for t, g in ts.groupby("Ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        if g.empty:
            continue
        # Senaste värdet
        price_0 = g["Close"].iloc[-1]
        # Pris bakåt (om saknas → NaN)
        def lag_close(periods):
            return g["Close"].shift(periods).iloc[-1] if len(g) > periods else np.nan

        price_1m  = lag_close(21)
        price_3m  = lag_close(63)
        price_6m  = lag_close(126)
        price_12m = lag_close(252)

        # Senaste SMA/returer (kan vara NaN om ej uppfyllda)
        sma50  = g["SMA50"].iloc[-1]
        sma200 = g["SMA200"].iloc[-1]
        ret1m  = g["Ret1m"].iloc[-1]
        ret3m  = g["Ret3m"].iloc[-1]
        ret6m  = g["Ret6m"].iloc[-1]
        ret12m = g["Ret12m"].iloc[-1]

        # En enkel momoscore (kan justeras senare)
        score_momo = np.nansum([ret1m, ret3m, ret6m, ret12m])

        rows.append({
            "Ticker": t,
            "Price_0": price_0,
            "Price_1m": price_1m,
            "Price_3m": price_3m,
            "Price_6m": price_6m,
            "Price_12m": price_12m,
            "SMA50": sma50,
            "SMA200": sma200,
            "Ret1m": ret1m,
            "Ret3m": ret3m,
            "Ret6m": ret6m,
            "Ret12m": ret12m,
            "Score_MOMO": score_momo
        })
    calc = pd.DataFrame(rows)
    # Sortera som i din vy (ex Ret6m desc)
    calc = calc.sort_values("Ret6m", ascending=False).reset_index(drop=True)
    return calc

def write_calc_only(calc_df: pd.DataFrame):
    """Kopiera mallen och skriv BARA Calc. Övriga flikar lämnas orörda."""
    if not TEMPLATE.exists():
        raise FileNotFoundError("Saknar Momentum_template.xlsx i repo-rooten.")
    shutil.copyfile(TEMPLATE, OUTPUT)

    # Rensa Calc-innehåll (behåll fliken) och skriv nya kolumner/rader
    wb = load_workbook(OUTPUT)
    if CALC_SHEET in wb.sheetnames:
        ws = wb[CALC_SHEET]
        ws.delete_rows(1, ws.max_row)
    else:
        wb.create_sheet(CALC_SHEET)
    wb.save(OUTPUT)

    with pd.ExcelWriter(OUTPUT, engine="openpyxl", mode="a", if_sheet_exists="overlay") as xw:
        calc_df.to_excel(xw, sheet_name=CALC_SHEET, index=False)

def clean_holdings_and_show_ok():
    """
    På fliken Holdings:
    - Ta bort all villkorsstyrd formatering & cellfärg
    - Visa OK/KÖP istället för 1/0 med *custom number format* (behåller ev. formler)
    """
    wb = load_workbook(OUTPUT)
    if HOLD_SHEET not in wb.sheetnames:
        wb.save(OUTPUT); return

    ws: Worksheet = wb[HOLD_SHEET]

    # 1) Ta bort all villkorsstyrd formatering
    try:
        ws.conditional_formatting._cf_rules.clear()
    except Exception:
        # olika openpyxl-versioner – om det skulle skära sig, sätt till tom lista
        ws.conditional_formatting = type(ws.conditional_formatting)()

    # 2) Rensa alla fills/färger (behåll värden & formler)
    for row in ws.iter_rows():
        for c in row:
            if c.fill is not None:
                c.fill = PatternFill(fill_type=None)

    # 3) Hitta kolumner med rubrikerna och sätt custom number format
    header_row = 1
    headers = { (cell.value or "").strip(): cell.column for cell in ws[header_row] if cell.value }

    def apply_format(col_name: str, fmt: str):
        if col_name in headers:
            col_idx = headers[col_name]
            for r in range(header_row + 1, ws.max_row + 1):
                cell = ws.cell(row=r, column=col_idx)
                # ändra endast om det är 0/1 eller formel som returnerar 0/1
                cell.number_format = fmt

    # Visa OK i stället för 1, tomt i stället för 0
    ok_fmt   = '[=1]"OK";[=0]"";General'
    kop_fmt  = '[=1]"KÖP";[=0]"";General'

    apply_format("FundOK", ok_fmt)
    apply_format("TrendOK", ok_fmt)
    apply_format("MomentumOK", ok_fmt)
    apply_format("KÖP?",    kop_fmt)

    wb.save(OUTPUT)

def main():
    # 1) Läs full historik från parquet
    raw = pd.read_parquet(CACHE)

    # 2) Timeserie-beräkningar
    ts = compute_timeseries(raw)

    # 3) EN-rads-vy per ticker för Calc med dina exakta kolumner
    calc = snapshot_calc(ts)

    # 4) Skriv bara Calc in i din mall
    write_calc_only(calc)

    # 5) Rensa färger i Holdings och visa OK/KÖP i stället för 1/0
    clean_holdings_and_show_ok()

if __name__ == "__main__":
    main()
