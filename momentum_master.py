# momentum_master.py — BuyNow fixad: exkludera tickers, rätt filter, QtyToBuy, placering efter Calc
import os, sys, re
import numpy as np
import pandas as pd
from shutil import copyfile
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

MALL_PATH = "Momentum mall fil.xlsx"
OUT_PATH  = "Momentum.xlsx"

# ------------- KONFIG -------------
# Tickers att alltid utesluta (case-insensitivt)
EXCLUDE_TICKERS = {"WOLF"}  # lägg till fler om du vill, t.ex. {"WOLF","XYZ"}
# ----------------------------------

def log(m): print(m, flush=True)
def fail(m):
    print(f"Error: {m}", file=sys.stderr, flush=True)
    sys.exit(1)

def to_num_series(s: pd.Series) -> pd.Series:
    if s.dtype.kind in "biufc":
        return pd.to_numeric(s, errors="coerce")
    x = s.astype(str).str.strip()
    x = x.str.replace("%", "", regex=False)
    x = x.str.replace(" ", "", regex=False)      # tusentalsblank
    x = x.str.replace("\u00A0", "", regex=False) # non-breaking space
    x = x.str.replace(",", ".", regex=False)     # svensk decimal
    return pd.to_numeric(x, errors="coerce")

# ---- Läs Calc från mallen ----
if not os.path.exists(MALL_PATH):
    fail(f"Mallen saknas: {MALL_PATH}")
try:
    calc = pd.read_excel(MALL_PATH, sheet_name="Calc")
except Exception as e:
    fail(f"Kunde inte läsa fliken 'Calc': {e}")

for must in ["Ticker", "Price_0", "SMA200"]:
    if must not in calc.columns:
        fail(f"Saknar kolumn i Calc: '{must}'")

# Arbets-DF
work = pd.DataFrame({"Ticker": calc["Ticker"].astype(str)})
work["Price"]  = to_num_series(calc["Price_0"])
work["SMA200"] = to_num_series(calc["SMA200"])

# Bygg returer från priskolumner (säkrast och jämförbart mot Avanza-logik)
def safe_ret(p0, p_back):
    p0 = to_num_series(p0); p_back = to_num_series(p_back)
    return (p0 / p_back) - 1.0

if "Price_1m"  in calc.columns: work["Ret_1m"]  = safe_ret(calc["Price_0"], calc["Price_1m"])
if "Price_3m"  in calc.columns: work["Ret_3m"]  = safe_ret(calc["Price_0"], calc["Price_3m"])
if "Price_6m"  in calc.columns: work["Ret_6m"]  = safe_ret(calc["Price_0"], calc["Price_6m"])
if "Price_12m" in calc.columns: work["Ret_12m"] = safe_ret(calc["Price_0"], calc["Price_12m"])

# Rank-kolumn
rank_col = None
for cand in ["Score_MOMO", "ScoreAdj", "Score", "MomentumScore", "Ret_6m", "Ret_3m"]:
    if cand in calc.columns:
        work[cand] = to_num_series(calc[cand])
        rank_col = cand
        break
if rank_col is None:
    rank_col = "Price"  # fallback

# EXCLUDE lista (WOLF m.fl.)
if not EXCLUDE_TICKERS:
    excl_mask = pd.Series(False, index=work.index)
else:
    excl_set = {t.upper() for t in EXCLUDE_TICKERS}
    excl_mask = work["Ticker"].str.upper().isin(excl_set)

# Hårt momentumfilter: Price_0 > SMA200 OCH alla returer > 0 (om kolumn finns)
flt = (work["Price"] > work["SMA200"].replace({np.nan: np.inf}))
for rc in ["Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
    if rc in work.columns:
        flt &= (work[rc].fillna(-1) > 0)

# Applicera filter och exkludering
cand = work.loc[flt & (~excl_mask)].dropna(subset=["Ticker"]).copy()

# Top 15
top = cand.sort_values(rank_col, ascending=False).head(15).copy()

# Fyll upp till 15 om färre: Price>SMA200 + icke-negativa returer + ej i EXCLUDE
need = 15 - len(top)
if need > 0:
    fill_mask = (work["Price"] > work["SMA200"].replace({np.nan: np.inf})) & (~excl_mask)
    for rc in ["Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
        if rc in work.columns:
            fill_mask &= (work[rc].fillna(-1) >= 0)
    filler = work.loc[fill_mask & (~work["Ticker"].isin(top["Ticker"]))].copy()
    filler = filler.sort_values(rank_col, ascending=False).head(need)
    buy_now = pd.concat([top, filler], ignore_index=True)
else:
    buy_now = top

# Exakt 15 unika tickers
buy_now = buy_now.drop_duplicates(subset=["Ticker"]).head(15).copy()

# Rang/flagga
buy_now.insert(0, "BuyRank", np.arange(1, len(buy_now) + 1))
buy_now["BuyFlag"] = buy_now["BuyRank"] <= 10

# Läs kapital från Parametrar (robust parsing)
def load_params() -> dict:
    try:
        dfp = pd.read_excel(MALL_PATH, sheet_name="Parametrar").iloc[:, :2].copy()
        dfp.columns = ["key","value"]
        dfp["key_norm"] = dfp["key"].astype(str).str.strip().str.lower()
        # försök göra value numeriskt om möjligt
        def parse_val(v):
            try:
                return float(re.sub(r"[ \u00A0]", "", str(v)).replace(",", "."))
            except:
                return v
        dfp["value"] = dfp["value"].apply(parse_val)
        return dict(zip(dfp["key_norm"], dfp["value"]))
    except Exception:
        return {}

params = load_params()
capital = 0.0
for k in ["kapital att handla för", "kapital", "kapital_att_handla_for"]:
    if k in params:
        try:
            capital = float(params[k]); break
        except: pass

per_ticker_budget = (capital / 10.0) if capital and capital > 0 else 0.0

# QtyToBuy för topp-10 (golvas), övriga = 0
buy_now["QtyToBuy"] = 0
if per_ticker_budget > 0:
    mask10 = buy_now["BuyRank"] <= 10
    qty = np.floor(per_ticker_budget / buy_now.loc[mask10, "Price"].replace(0, np.nan)).fillna(0).astype(int)
    buy_now.loc[mask10, "QtyToBuy"] = qty

log(f"[INFO] Kapital: {capital} | Per-ticker (10 st): {per_ticker_budget} | Sum qty(top10): {int(buy_now.loc[buy_now['BuyRank']<=10,'QtyToBuy'].sum())}")

# Export-DF: returer som DECIMALER (0.1234), visas som % i Excel
export_df = buy_now.copy()
# runda övriga numeriska till 2 dec (inte QtyToBuy eller Ret_*)
num_cols = export_df.select_dtypes(include=[np.number]).columns.tolist()
for col in num_cols:
    if col not in ["QtyToBuy", "Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
        export_df[col] = export_df[col].round(2)
export_df = export_df.sort_values("BuyRank").reset_index(drop=True)

# Kopiera mallen → skriv endast BuyNow och placera direkt efter Calc
copyfile(MALL_PATH, OUT_PATH)
wb = load_workbook(OUT_PATH)

if "BuyNow" in wb.sheetnames:
    wb.remove(wb["BuyNow"])

if "Calc" not in wb.sheetnames:
    fail("Fliken 'Calc' saknas i utfilen.")
calc_index = wb.sheetnames.index("Calc")
ws = wb.create_sheet("BuyNow", index=calc_index + 1)

# Skriv header + data
headers = list(export_df.columns)
for j, h in enumerate(headers, start=1):
    ws.cell(row=1, column=j, value=h)
for i, row in export_df.iterrows():
    for j, h in enumerate(headers, start=1):
        ws.cell(row=i+2, column=j, value=row[h])

# Format: Ret_* som 0.00%, QtyToBuy heltal, övriga numeriska 0.00
hdr_idx = {h: i+1 for i, h in enumerate(headers)}

def fmt_col(col_name, fmt):
    if col_name not in hdr_idx: return
    c = hdr_idx[col_name]
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=c).number_format = fmt

for c in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
    if c in hdr_idx: fmt_col(c, "0.00%")
if "QtyToBuy" in hdr_idx: fmt_col("QtyToBuy", "0")

for name in headers:
    if name not in {"Ret_1m","Ret_3m","Ret_6m","Ret_12m","QtyToBuy"}:
        c = hdr_idx[name]
        for r in range(2, ws.max_row + 1):
            cell = ws.cell(row=r, column=c)
            if isinstance(cell.value, (int, float)):
                cell.number_format = "0.00"

# Enkel autofit
for idx, name in enumerate(headers, start=1):
    maxlen = len(str(name))
    for r in range(2, ws.max_row + 1):
        v = ws.cell(row=r, column=idx).value
        if v is not None:
            maxlen = max(maxlen, len(str(v)))
    ws.column_dimensions[get_column_letter(idx)].width = min(maxlen + 2, 50)

wb.save(OUT_PATH)
log("[OK] Momentum.xlsx uppdaterad — BuyNow efter Calc, WOLF exkluderad, QtyToBuy ifyllt.")
