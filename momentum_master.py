import pandas as pd
import numpy as np

INPUT = "momentum_data.xlsx"
OUTPUT = "Momentum.xlsx"

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

def main():
    raw = pd.read_excel(INPUT)
    ind = compute(raw)
    hold = holdings_view(ind)
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as xw:
        ind.to_excel(xw, sheet_name="Calc", index=False)
        hold.to_excel(xw, sheet_name="Holdings", index=False)

if __name__ == "__main__":
    main()
