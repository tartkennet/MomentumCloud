import pandas as pd
import numpy as np
from openpyxl import load_workbook
import shutil
from pathlib import Path

TEMPLATE = Path("Momentum_template.xlsx")   # Din mall med ALLA flikar
OUTPUT   = Path("Momentum.xlsx")            # Filen som byggs/skickas
INPUT    = Path("momentum_data.xlsx")       # Prisdata från fetch-steget

CALC_SHEET = "Calc"
HOLD_SHEET = "Holdings"

def compute(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["Ticker","date"])
    def per_t(g):
        g = g.sort_values("date")
        g["SMA50"]  = g["Close"].rolling(50, min_periods=10).mean()
        g["SMA200"] = g["Close"].rolling(200, min_periods=20).mean()
        def pct(d): return g["Close"].pct_change(d)
        g["Ret1m"]  = pct(21)
        g["Ret3m"]  = pct(63)
        g["Ret6m"]  = pct(126)
        g["Ret12m"] = pct(252)
        g["TrendOK"]    = (g["SMA50"] > g["SMA200"]).astype(int)
        g["MomentumOK"] = (g["Ret3m"] > 0).astype(int)
        g["FundOK"]     = 1
        g["Signal"]     = np.where(g["TrendOK"] & g["MomentumOK"], "HÅLL", "SÄLJ")
        g["KÖP?"]       = (g["TrendOK"] & g["MomentumOK"]).astype(int)
        return g
    return df.groupby("Ticker", group_keys=False).apply(per_t)

def holdings_view(df):
    latest = df.sort_values("date").groupby("Ticker").tail(1).reset_index(drop=True)
    latest = latest.rename(columns={"date":"LastDate","Close":"LastPrice"})
    latest["FundOK_txt"]     = latest["FundOK"].map({1:"OK",0:""})
    latest["TrendOK_txt"]    = latest["TrendOK"].map({1:"OK",0:""})
    latest["MomentumOK_txt"] = latest["MomentumOK"].map({1:"OK",0:""})
    latest["KÖP_txt"]        = latest["KÖP?"].map({1:"KÖP",0:""})
    latest = latest.sort_values("Ret6m", ascending=False)
    return latest

def write_into_template(calc_df: pd.DataFrame, hold_df: pd.DataFrame):
    if not TEMPLATE.exists():
        raise FileNotFoundError("Saknar Momentum_template.xlsx i repo-rooten.")
    shutil.copyfile(TEMPLATE, OUTPUT)

    wb = load_workbook(OUTPUT)
    for sheet_name in [CALC_SHEET, HOLD_SHEET]:
        if sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            ws.delete_rows(1, ws.max_row)  # rensa allt innehåll, behåll fliken
        else:
            wb.create_sheet(sheet_name)
    wb.save(OUTPUT)

    with pd.ExcelWriter(OUTPUT, engine="openpyxl", mode="a", if_sheet_exists="overlay") as xw:
        calc_df.to_excel(xw, sheet_name=CALC_SHEET, index=False)
        hold_df.to_excel(xw, sheet_name=HOLD_SHEET, index=False)

def main():
    raw = pd.read_excel(INPUT)
    ind = compute(raw)
    hold = holdings_view(ind)
    write_into_template(ind, hold)

if __name__ == "__main__":
    main()
