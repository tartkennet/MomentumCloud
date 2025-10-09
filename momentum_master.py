# momentum_master.py – robust & rättade procenttal
# - Universe orörd (kopieras från mallen).
# - BuyNow = 15 (Price_0 > SMA200, Ret3m>0, Ret6m>0; fyll upp med Price_0 > SMA200).
# - Endast topp-10 får QtyToBuy, baserat på Parametrar["Kapital att handla för"].
# - Returkolumner i Excel visas som 0.00% (utan att multiplicera värdet).
# - Övriga numeriska i BuyNow visas som 0.00, QtyToBuy som heltal.

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

# --------- helpers ----------
def normalize_name(s: str) -> str:
    return (str(s).strip().lower()
            .replace(" ", "").replace("_", "").replace("-", "").replace("%",""))

def to_float_series(s: pd.Series) -> pd.Series:
    if s.dtype.kind in "biufc":
        return pd.to_numeric(s, errors="coerce")
    x = s.astype(str)
    x = x.str.replace("%","", regex=False).str.strip()
    x = x.str.replace(" ", "", regex=False)       # thousand sep (space)
    x = x.str.replace(",", ".", regex=False)      # Swedish decimal
    return pd.to_numeric(x, errors="coerce")

def ensure_decimal_returns(sr: pd.Series) -> pd.Series:
    v = pd.to_numeric(sr, errors="coerce")
    # if values look like 12.34 (i.e., 12.34%) convert to decimal 0.1234
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

# --------- read mall ----------
if not os.path.exists(MALL_PATH):
    fail(f"Mallen saknas: {MALL_PATH}")
try:
    base = pd.read_excel(MALL_PATH, sheet_name="Calc")
except Exception as e:
    fail(f"Kunde inte läsa fliken 'Calc': {e}")

if "Ticker" not in base.columns:
    fail("Kolumnen 'Ticker' saknas i Calc.")

# --------- aliases (enl. din Calc-bild) ----------
price_alias  = ["Price_0", "Price", "Close", "Adj Close", "AdjClose", "Last"]
sma200_alias = ["SMA200", "SMA_200", "MA200", "MA_200"]
ret1_alias   = ["Ret1m", "Ret_1m", "R1m", "Return1m"]
ret3_alias   = ["Ret3m", "Ret_3m", "R3m", "Return3m"]
ret6_alias   = ["Ret6m", "Ret_6m", "R6m", "Return6m"]
ret12_alias  = ["Ret12m","Ret_12m","R12m","Return12m"]
rank_alias   = ["ScoreAdj", "Score_MOMO", "Score", "MomentumScore", "Ret6m", "Ret_6m", "Ret3m", "Ret_3m"]

price_col, price   = pick(base, price_alias,  required=True)
sma200_col, sma200 = pick(base, sma200_alias, required=True)
ret1_col, ret1     = pick(base, ret1_alias)
ret3_col, ret3     = pick(base, ret3_alias)
ret6_col, ret6     = pick(base, ret6_alias)
ret12_col, ret12   = pick(base, ret12_alias)

if price is None or sma200 is None:
    miss = []
    if price is None: miss.append("Price_0/Price/Close")
    if sma200 is None: miss.append("SMA200/MA200")
    fail(f"Saknade kolumner i Calc: {miss}")

# returns as decimals internally
if ret1  is not None:  ret1  = ensure_decimal_returns(ret1)
if ret3  is not None:  ret3  = ensure_decimal_returns(ret3)
if ret6  is not None:  ret6  = ensure_decimal_returns(ret6)
if ret12 is not None:  ret12 = ensure_decimal_returns(ret12)

# working DF
work = pd.DataFrame({"Ticker": base["Ticker"]})
work["Price"]  = price
work["SMA200"] = sma200
if ret1  is not None: work["Ret_1m"]  = ret1
if ret3  is not None: work["Ret_3m"]  = ret3
if ret6  is not None: work["Ret_6m"]  = ret6
if ret12 is not None: work["Ret_12m"] = ret12

# ranking column
for a in rank_alias:
    if a in base.columns:
        work[a] = to_float_series(base[a])
        rank_col = a
        break
else:
    rank_col = "Price"

log(f"Mapping: Price='{price_col}', SMA200='{sma200_col}', "
    f"Ret1='{ret1_col}', Ret3='{ret3_col}', Ret6='{ret6_col}', Ret12='{ret12_col}', rank='{rank_col}'")

# --------- core filter (YES: Price_0 > SMA200 is included) ----------
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

# kapital & QtyToBuy
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

# --------- export (NO extra *100 on returns) ----------
export_df = buy_now_df.copy()

# round other numerics to two decimals; keep returns as decimals (Excel will format them)
num_cols = export_df.select_dtypes(include=[np.number]).columns.tolist()
for col in num_cols:
    if col not in ["QtyToBuy", "Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
        export_df[col] = export_df[col].round(2)
export_df = export_df.sort_values("BuyRank").reset_index(drop=True)

# copy mall -> write only BuyNow
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

# formats: returns as percent, qty int, others two decimals
header_map = {h:i+1 for i,h in enumerate(headers)}
def fmt_col(name, fmt):
    col = header_map.get(name); 
    if not col: return
    for r in range(2, ws.max_row+1):
        ws.cell(row=r, column=col).number_format = fmt

for c in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
    if c in header_map: fmt_col(c, "0.00%")   # uses decimal values (e.g., 0.1234 -> 12.34%)
if "QtyToBuy" in header_map: fmt_col("QtyToBuy", "0")
for name in headers:
    if name not in {"Ret_1m","Ret_3m","Ret_6m","Ret_12m","QtyToBuy"}:
        # set 0.00 only for numeric values
        col = header_map[name]
        for r in range(2, ws.max_row+1):
            cell = ws.cell(row=r, column=col)
            if isinstance(cell.value, (int, float)):
                cell.number_format = "0.00"

# simple autofit
for idx,name in enumerate(headers, start=1):
    maxlen = len(str(name))
    for r in range(2, ws.max_row+1):
        v = ws.cell(row=r, column=idx).value
        if v is not None: maxlen = max(maxlen, len(str(v)))
    ws.column_dimensions[get_column_letter(idx)].width = min(maxlen+2, 50)

wb.save(OUT_PATH)

# optional debug for WOLF
try:
    dbg = buy_now_df.loc[buy_now_df["Ticker"].astype(str).str.upper()=="WOLF"].iloc[0]
    log(f"DBG WOLF: Price={dbg.get('Price')}, SMA200={dbg.get('SMA200')}, "
        f"Ret3m(dec)={dbg.get('Ret_3m')}, Ret6m(dec)={dbg.get('Ret_6m')}")
except Exception:
    pass

log("[OK] Momentum.xlsx uppdaterad (BuyNow fixad, procent korrekt).")
