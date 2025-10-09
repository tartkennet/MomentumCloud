# momentum_master.py — Portföljvärde (Parametrar!B1), auto-USDSEK, QtyToBuy för topp-10
import os, sys, re
import numpy as np
import pandas as pd
from shutil import copyfile
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import requests

MALL_PATH = "Momentum mall fil.xlsx"
OUT_PATH  = "Momentum.xlsx"
EXCLUDE_TICKERS = {"WOLF"}  # blocklista

def log(m): print(m, flush=True)
def fail(m): print(f"Error: {m}", file=sys.stderr, flush=True); sys.exit(1)

def to_num_series(s: pd.Series) -> pd.Series:
    if getattr(s, "dtype", None) is not None and s.dtype.kind in "biufc":
        return pd.to_numeric(s, errors="coerce")
    x = pd.Series(s, dtype="object").astype(str).str.strip()
    x = x.str.replace("%","",regex=False).str.replace("\u00A0","",regex=False).str.replace(" ","",regex=False)
    x = x.str.replace(",",".",regex=False)
    return pd.to_numeric(x, errors="coerce")

# ---------- Läs Calc ----------
if not os.path.exists(MALL_PATH): fail(f"Mallen saknas: {MALL_PATH}")
calc = pd.read_excel(MALL_PATH, sheet_name="Calc")

for must in ["Ticker","Price_0","SMA200"]:
    if must not in calc.columns: fail(f"Saknar kolumn i Calc: '{must}'")

work = pd.DataFrame({"Ticker": calc["Ticker"].astype(str)})
work["Price"]  = to_num_series(calc["Price_0"])
work["SMA200"] = to_num_series(calc["SMA200"])

def safe_ret(p0,pb):
    p0 = to_num_series(p0); pb = to_num_series(pb); return (p0/pb)-1.0
if "Price_1m"  in calc.columns: work["Ret_1m"]  = safe_ret(calc["Price_0"], calc["Price_1m"])
if "Price_3m"  in calc.columns: work["Ret_3m"]  = safe_ret(calc["Price_0"], calc["Price_3m"])
if "Price_6m"  in calc.columns: work["Ret_6m"]  = safe_ret(calc["Price_0"], calc["Price_6m"])
if "Price_12m" in calc.columns: work["Ret_12m"] = safe_ret(calc["Price_0"], calc["Price_12m"])

# Rangkolumn
rank_col = None
for c in ["Score_MOMO","ScoreAdj","Score","MomentumScore","Ret_6m","Ret_3m"]:
    if c in calc.columns: work[c]=to_num_series(calc[c]); rank_col=c; break
if rank_col is None: rank_col="Price"

# ---------- Filter + exkludering ----------
excl = work["Ticker"].str.upper().isin({t.upper() for t in EXCLUDE_TICKERS})
flt = (work["Price"] > work["SMA200"].replace({np.nan: np.inf}))
for rc in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
    if rc in work.columns: flt &= (work[rc].fillna(-1) > 0)

cand = work.loc[flt & ~excl].dropna(subset=["Ticker"]).copy()
top  = cand.sort_values(rank_col, ascending=False).head(15)
need = 15 - len(top)
if need>0:
    fill = (work["Price"] > work["SMA200"].replace({np.nan: np.inf})) & ~excl
    for rc in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
        if rc in work.columns: fill &= (work[rc].fillna(-1) >= 0)
    filler = work.loc[fill & (~work["Ticker"].isin(top["Ticker"]))].sort_values(rank_col, ascending=False).head(need)
    buy_now = pd.concat([top, filler], ignore_index=True)
else:
    buy_now = top.copy()

buy_now = buy_now.drop_duplicates(subset=["Ticker"]).head(15).copy()
buy_now.insert(0,"BuyRank", np.arange(1, len(buy_now)+1))
buy_now["BuyFlag"] = buy_now["BuyRank"] <= 10

# ---------- Portföljvärde (SEK) från Parametrar!B1 ----------
try:
    # exakt cell B1
    port_df = pd.read_excel(MALL_PATH, sheet_name="Parametrar", header=None)
    portfolio_value = port_df.iat[0,1]  # B1
    try:
        portfolio_value = float(str(portfolio_value).replace("\u00A0","").replace(" ","").replace(",","."))
    except:
        portfolio_value = 0.0
except Exception:
    portfolio_value = 0.0

log(f"[INFO] Portföljvärde(SEK) = {portfolio_value}")

# ---------- USDSEK från Polygon ----------
def fetch_usdsek(default=11.0):
    api = os.getenv("POLYGON_API_KEY","").strip()
    if not api:
        log("[WARN] POLYGON_API_KEY saknas – använder fallback USDSEK.")
        return default,"fallback"
    try:
        url=f"https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev?adjusted=true&apiKey={api}"
        r=requests.get(url,timeout=15); r.raise_for_status()
        close=float(r.json()["results"][0]["c"])
        if close<=0: raise ValueError("USDSEK<=0")
        return close,"polygon"
    except Exception as e:
        log(f"[WARN] USDSEK misslyckades ({e}) – fallback {default}.")
        return default,"fallback"

usdsek,src = fetch_usdsek(11.0)
log(f"[INFO] USDSEK = {usdsek} ({src})")

# ---------- QtyToBuy för topp-10 ----------
per_ticker_budget_sek = (portfolio_value/10.0) if portfolio_value and portfolio_value>0 else 0.0
buy_now["QtyToBuy"] = 0
if per_ticker_budget_sek>0 and usdsek>0:
    m = buy_now["BuyRank"]<=10
    price_sek = buy_now.loc[m,"Price"] * usdsek
    qty = np.floor(per_ticker_budget_sek / price_sek.replace(0,np.nan)).fillna(0).astype(int)
    buy_now.loc[m,"QtyToBuy"] = qty
    if m.any():
        f = buy_now[m].iloc[0]
        log(f"[DBG] Exempel: {f['Ticker']} PriceUSD={f['Price']}, PriceSEK={f['Price']*usdsek:.2f}, "
            f"BudgetSEK={per_ticker_budget_sek}, Qty={int(f['QtyToBuy'])}")
else:
    log("[WARN] Portföljvärde eller USDSEK = 0 → QtyToBuy blir 0")

# ---------- Export & skriv BuyNow EFTER Calc ----------
export_df = buy_now.copy()
# runda övriga numeriska till 2 dec (ej QtyToBuy/Ret_*)
num_cols = export_df.select_dtypes(include=[np.number]).columns.tolist()
for col in num_cols:
    if col not in ["QtyToBuy","Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
        export_df[col]=export_df[col].round(2)
export_df = export_df.sort_values("BuyRank").reset_index(drop=True)

copyfile(MALL_PATH, OUT_PATH)
wb = load_workbook(OUT_PATH)

# BuyNow efter Calc
if "BuyNow" in wb.sheetnames: wb.remove(wb["BuyNow"])
if "Calc" not in wb.sheetnames: fail("Calc saknas i utfilen.")
calc_idx = wb.sheetnames.index("Calc")
ws = wb.create_sheet("BuyNow", index=calc_idx+1)

# skriv BuyNow
headers=list(export_df.columns)
for j,h in enumerate(headers,1): ws.cell(row=1,column=j,value=h)
for i,row in export_df.iterrows():
    for j,h in enumerate(headers,1):
        ws.cell(row=i+2,column=j,value=row[h])

# format
hdr={h:i+1 for i,h in enumerate(headers)}
def fmt(col, fmt):
    if col not in hdr: return
    c = hdr[col]
    for r in range(2, ws.max_row+1):
        ws.cell(row=r, column=c).number_format = fmt

for c in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
    fmt(c, "0.00%")
if "QtyToBuy" in hdr: fmt("QtyToBuy","0")
for name in headers:
    if name not in {"Ret_1m","Ret_3m","Ret_6m","Ret_12m","QtyToBuy"}:
        c = hdr[name]
        for r in range(2, ws.max_row+1):
            cell = ws.cell(row=r, column=c)
            if isinstance(cell.value, (int, float)):
                cell.number_format = "0.00"

# lägg även in USDSEK i Parametrar (OUT) för spårbarhet
if "Parametrar" in wb.sheetnames:
    ws_p = wb["Parametrar"]
    try:
        ws_p.cell(row=1, column=1, value="Portföljvärde")  # bevara etiketten
        ws_p.cell(row=1, column=2, value=float(portfolio_value))
    except: pass
    # skriv/uppdatera USDSEK på rad 2
    ws_p.cell(row=2, column=1, value="USDSEK")
    ws_p.cell(row=2, column=2, value=float(usdsek))

# enkel autofit
for col_idx,name in enumerate(headers, start=1):
    maxlen = len(str(name))
    for r in range(2, ws.max_row+1):
        v = ws.cell(row=r, column=col_idx).value
        if v is not None: maxlen = max(maxlen, len(str(v)))
    ws.column_dimensions[get_column_letter(col_idx)].width = min(maxlen+2, 50)

wb.save(OUT_PATH)
log("[OK] Momentum.xlsx uppdaterad — Portföljvärde från Parametrar!B1, QtyToBuy ifyllt för topp-10.")
