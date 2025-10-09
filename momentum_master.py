# momentum_master.py – anpassad till Calc-rubrikerna:
# Ticker, Price_0, Price_1m, Price_3m, Price_6m, Price_12m, SMA50, SMA200,
# Ret1m, Ret3m, Ret6m, Ret12m, Score_MOMO
# - Bygger ENDAST BuyNow enligt reglerna: 15 rader; Price>SMA200 & Ret3m>0 & Ret6m>0,
#   fyll upp till 15 med Price>SMA200. QtyToBuy bara för topp 10.
# - Returkolumner i Excel: 0.00%, övriga tal 0.00, QtyToBuy heltal.
# - Kopierar mallen till Momentum.xlsx och ersätter bara BuyNow-fliken.

import os, sys
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from shutil import copyfile

MALL_PATH = "Momentum mall fil.xlsx"
OUT_PATH  = "Momentum.xlsx"

def log(msg): print(msg, flush=True)
def fail(msg):
    print(f"Error: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)

# ---------- hjälp ----------
def normalize_name(s: str) -> str:
    return (str(s).strip().lower()
            .replace(" ", "").replace("_", "").replace("-", "").replace("%",""))

def to_float_series(s: pd.Series) -> pd.Series:
    if s.dtype.kind in "biufc":
        return pd.to_numeric(s, errors="coerce")
    x = s.astype(str)
    x = x.str.replace("%","", regex=False).str.strip()
    x = x.str.replace(" ", "", regex=False)       # tusentals-mellanrum
    x = x.str.replace(",", ".", regex=False)      # svensk decimal
    return pd.to_numeric(x, errors="coerce")

def ensure_decimal_returns(sr: pd.Series) -> pd.Series:
    v = pd.to_numeric(sr, errors="coerce")
    return v.where(v.abs() <= 1, v / 100.0)

def pick(df: pd.DataFrame, aliases: list, required=False):
    norm_map = {normalize_name(c): c for c in df.columns}
    for a in aliases:
        key = normalize_name(a)
        if key in norm_map:
            col = norm_map[key]
            return col, to_float_series(df[col])
    if required:
        return None, None
    return None, None

# ---------- läsa mall ----------
if not os.path.exists(MALL_PATH):
    fail(f"Mallen saknas: {MALL_PATH}")
try:
    base = pd.read_excel(MALL_PATH, sheet_name="Calc")
except Exception as e:
    fail(f"Kunde inte läsa fliken 'Calc': {e}")

if "Ticker" not in base.columns:
    fail("Kolumnen 'Ticker' saknas i Calc.")

# ---------- alias enligt din bild ----------
price_alias  = ["Price_0", "Price", "Close", "Adj Close", "AdjClose", "Last"]
sma200_alias = ["SMA200", "SMA_200", "MA200", "MA_200"]
ret1_alias   = ["Ret1m", "Ret_1m", "R1m", "Return1m"]
ret3_alias   = ["Ret3m", "Ret_3m", "R3m", "Return3m"]
ret6_alias   = ["Ret6m", "Ret_6m", "R6m", "Return6m"]
ret12_alias  = ["Ret12m","Ret_12m","R12m","Return12m"]
rank_alias   = ["ScoreAdj", "Score_MOMO", "Score", "MomentumScore", "Ret6m", "Ret_6m", "Ret3m", "Ret_3m"]

price_col, price = pick(base, price_alias, required=True)
sma200_col, sma200 = pick(base, sma200_alias, required=True)
ret1_col, ret1 = pick(base, ret1_alias, required=False)
ret3_col, ret3 = pick(base, ret3_alias, required=False)
ret6_col, ret6 = pick(base, ret6_alias, required=False)
ret12_col, ret12 = pick(base, ret12_alias, required=False)

if price is None or sma200 is None:
    miss = []
    if price is None: miss.append("Price_0/Price/Close")
    if sma200 is None: miss.append("SMA200/MA200")
    fail(f"Saknade kolumner i Calc: {miss}")

# retur → decimal internt
if ret1  is not None: ret1  = ensure_decimal_returns(ret1)
if ret3  is not None: ret3  = ensure_decimal_returns(ret3)
if ret6  is not None: ret6  = ensure_decimal_returns(ret6)
if ret12 is not None: ret12 = ensure_decimal_returns(ret12)

# bygg arbets-DF
work = pd.DataFrame({"Ticker": base["Ticker"]})
work["Price"]  = price
work["SMA200"] = sma200
if ret1  is not None: work["Ret_1m"]  = ret1
if ret3  is not None: work["Ret_3m"]  = ret3
if ret6  is not None: work["Ret_6m"]  = ret6
if ret12 is not None: work["Ret_12m"] = ret12

# ranking
for a in rank_alias:
    if a in base.columns:
        work[a] = to_float_series(base[a])
        rank_col = a
        break
else:
    rank_col = "Price"  # sista utväg

log(f"Mapping: Price='{price_col}', SMA200='{sma200_col}', "
    f"Ret1='{ret1_col}', Ret3='{ret3_col}', Ret6='{ret6_col}', Ret12='{ret12_col}', rank='{rank_col}'")

# ---------- filter & urval ----------
flt = (work["Price"] > work["SMA200"].replace({np.nan: np.inf}))
if "Ret_3m" in work.columns: flt &= (work["Ret_3m"].fillna(-1) > 0)
else: log("VARNING: Ret_3m saknas – hoppar över det filtret.")
if "Ret_6m" in work.columns: flt &= (work["Ret_6m"].fillna(-1) > 0)
else: log("VARNING: Ret_6m saknas – hoppar över det filtret.")

cand = work.loc[flt].dropna(subset=["Ticker"]).copy()
top_core = cand.sort_values(rank_col, ascending=False).head(15)
need = 15 - len(top_core)
if need > 0:
    trend = work.loc[(work["Price"] > work["SMA200"].replace({np.nan: np.inf}))].copy()
    trend = trend[~trend["Ticker"].isin(top_core["Ticker"])]
    filler = trend.sort_values(rank_col, ascending=False).head(need)
    buy_now_df = pd.concat([top_core, filler], ignore_index=True)
else:
    buy_now_df = top_core.copy()

buy_now_df = buy_now_df.drop_duplicates(subset=["Ticker"]).head(15).copy()
buy_now_df.insert(0, "BuyRank", np.arange(1, len(buy_now_df)+1))
buy_now_df["BuyFlag"] = buy_now_df["BuyRank"] <= 10

# kapital
def load_params_dict(mall_path: str) -> dict:
    try:
        dfp = pd.read_excel(mall_path, sheet_name="Parametrar")
        kv = dfp.iloc[:, :2].copy()
        kv.columns = ["key","value"]
        kv["key_norm"] = kv["key"].astype(str).str.strip().str.lower()
        return dict(zip(kv["key_norm"], kv["value"]))
    except Exception:
        return {}

params = load_params_dict(MALL_PATH)
capital = 0.0
for k in ["kapital att handla för","kapital","kapital_att_handla_for"]:
    if k in params:
        try:
            capital = float(params[k]); break
        except: pass

per_ticker_budget = (capital/10.0) if capital>0 else 0.0
buy_now_df["QtyToBuy"] = 0
if per_ticker_budget>0 and "Price" in buy_now_df.columns:
    m = buy_now_df["BuyRank"] <= 10
    qty = np.floor(per_ticker_budget / buy_now_df.loc[m,"Price"].replace(0,np.nan)).fillna(0).astype(int)
    buy_now_df.loc[m,"QtyToBuy"] = qty

# export: procent/decimaler
export_df = buy_now_df.copy()
for c in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
    if c in export_df.columns:
        export_df[c] = (pd.to_numeric(export_df[c], errors="coerce")*100).round(2)

num_cols = export_df.select_dtypes(include=[np.number]).columns.tolist()
for col in num_cols:
    if col not in ["QtyToBuy","Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
        export_df[col] = export_df[col].round(2)
export_df = export_df.sort_values("BuyRank").reset_index(drop=True)

# skriv endast BuyNow – kopiera mallen först
from shutil import copyfile
copyfile(MALL_PATH, OUT_PATH)

wb = load_workbook(OUT_PATH)
if "BuyNow" in wb.sheetnames: wb.remove(wb["BuyNow"])
ws = wb.create_sheet("BuyNow")

# headers + data
headers = list(export_df.columns)
for j,h in enumerate(headers, start=1): ws.cell(row=1, column=j, value=h)
for i,row in export_df.iterrows():
    for j,h in enumerate(headers, start=1):
        ws.cell(row=i+2, column=j, value=row[h])

# format
header_map = {h:i+1 for i,h in enumerate(headers)}
def fmt_col(name, fmt):
    col = header_map.get(name); 
    if not col: return
    for r in range(2, ws.max_row+1):
        ws.cell(row=r, column=col).number_format = fmt

for c in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
    if c in header_map: fmt_col(c, "0.00%")
if "QtyToBuy" in header_map: fmt_col("QtyToBuy", "0")
for name in headers:
    if name not in {"Ret_1m","Ret_3m","Ret_6m","Ret_12m","QtyToBuy"}:
        # sätt 0.00 endast om numeriskt
        col = header_map[name]
        for r in range(2, ws.max_row+1):
            cell = ws.cell(row=r, column=col)
            if isinstance(cell.value, (int,float)):
                cell.number_format = "0.00"

# enkel autofit
for idx,name in enumerate(headers, start=1):
    maxlen = len(str(name))
    for r in range(2, ws.max_row+1):
        v = ws.cell(row=r, column=idx).value
        if v is not None: maxlen = max(maxlen, len(str(v)))
    ws.column_dimensions[get_column_letter(idx)].width = min(maxlen+2, 50)

wb.save(OUT_PATH)
log("[OK] Momentum.xlsx uppdaterad (BuyNow = 15, QtyToBuy för topp-10).")
