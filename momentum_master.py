# momentum_master.py – BuyNow korrekt enligt dina regler
# - Returer räknas från Price_0/1m/3m/6m/12m => (Price_0/Price_Nm - 1)
# - Filter: Price_0 > SMA200 OCH Ret_1m>0 OCH Ret_3m>0 OCH Ret_6m>0 OCH Ret_12m>0
# - 15 rader i BuyNow (om färre, fyll upp med Price_0>SMA200 + icke-negativa returer)
# - Endast topp-10 får QtyToBuy (från Parametrar["Kapital att handla för"])
# - BuyNow-fliken placeras direkt efter Calc
# - Returkolumner visas som 0.00%, övriga som 0.00, QtyToBuy som heltal
# - Universe och övriga flikar lämnas orörda (vi kopierar mallen och ersätter bara BuyNow)

import os, sys
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from shutil import copyfile

MALL_PATH = "Momentum mall fil.xlsx"
OUT_PATH  = "Momentum.xlsx"

def log(m): print(m, flush=True)
def fail(m):
    print(f"Error: {m}", file=sys.stderr, flush=True)
    sys.exit(1)

# ---------- Läs in mallens Calc ----------
if not os.path.exists(MALL_PATH):
    fail(f"Mallen saknas: {MALL_PATH}")

try:
    calc = pd.read_excel(MALL_PATH, sheet_name="Calc")
except Exception as e:
    fail(f"Kunde inte läsa fliken 'Calc': {e}")

if "Ticker" not in calc.columns:
    fail("Kolumnen 'Ticker' saknas i Calc.")

# Alias för dina rubriker (enligt din skärmdump)
def get_col(name_options):
    for n in name_options:
        if n in calc.columns:
            return n
    return None

COL_PRICE0 = get_col(["Price_0", "Price0", "Close", "Price"])
COL_P1M    = get_col(["Price_1m", "Price1m"])
COL_P3M    = get_col(["Price_3m", "Price3m"])
COL_P6M    = get_col(["Price_6m", "Price6m"])
COL_P12M   = get_col(["Price_12m", "Price12m"])
COL_SMA200 = get_col(["SMA200", "MA200"])
COL_SCORE  = get_col(["Score_MOMO", "ScoreAdj", "Score", "MomentumScore"])

need = [("Price_0", COL_PRICE0), ("SMA200", COL_SMA200)]
missing = [n for n,c in need if c is None]
if missing:
    fail(f"Saknar nödvändiga kolumner i Calc: {missing}")

# Bygg arbets-DF
work = pd.DataFrame({"Ticker": calc["Ticker"]})
work["Price"]  = pd.to_numeric(calc[COL_PRICE0], errors="coerce")
work["SMA200"] = pd.to_numeric(calc[COL_SMA200], errors="coerce")

# Räkna returer från pris-kolumner om de finns
def safe_ret(p0, p_back):
    p0 = pd.to_numeric(p0, errors="coerce")
    p_back = pd.to_numeric(p_back, errors="coerce")
    return (p0 / p_back) - 1.0

if COL_P1M  is not None: work["Ret_1m"]  = safe_ret(calc[COL_PRICE0], calc[COL_P1M])
if COL_P3M  is not None: work["Ret_3m"]  = safe_ret(calc[COL_PRICE0], calc[COL_P3M])
if COL_P6M  is not None: work["Ret_6m"]  = safe_ret(calc[COL_PRICE0], calc[COL_P6M])
if COL_P12M is not None: work["Ret_12m"] = safe_ret(calc[COL_PRICE0], calc[COL_P12M])

# Rank-kolumn (fall back till Price om inget score)
rank_col = COL_SCORE if COL_SCORE is not None else "Price"
if rank_col != "Price":
    work[rank_col] = pd.to_numeric(calc[rank_col], errors="coerce")

# ---------- Hårdare filter så WOLF & liknande ryker ----------
flt = (
    (work["Price"] > work["SMA200"].replace({np.nan: np.inf})) &
    (work.get("Ret_1m", 0).fillna(-1)  > 0) &
    (work.get("Ret_3m", 0).fillna(-1) > 0) &
    (work.get("Ret_6m", 0).fillna(-1) > 0) &
    (work.get("Ret_12m", 0).fillna(-1) > 0)
)

candidates = work.loc[flt].dropna(subset=["Ticker"]).copy()

# Topp 15
top = candidates.sort_values(rank_col, ascending=False).head(15).copy()

# Fyll upp till 15 om färre än 15 klarar filtret:
need = 15 - len(top)
if need > 0:
    # Fyllare: Price>SMA200 och inga negativa returer (så vi inte drar in "röda" bolag)
    filler_mask = (work["Price"] > work["SMA200"].replace({np.nan: np.inf}))
    for rc in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
        if rc in work.columns:
            filler_mask &= (work[rc].fillna(-1) >= 0)
    filler = work.loc[filler_mask & (~work["Ticker"].isin(top["Ticker"]))].copy()
    filler = filler.sort_values(rank_col, ascending=False).head(need)
    buy_now_df = pd.concat([top, filler], ignore_index=True)
else:
    buy_now_df = top

# Exakt 15 unika
buy_now_df = buy_now_df.dropna(subset=["Ticker"]).drop_duplicates(subset=["Ticker"]).head(15).copy()

# ---------- Rang, flagga, QtyToBuy ----------
buy_now_df.insert(0, "BuyRank", np.arange(1, len(buy_now_df)+1))
buy_now_df["BuyFlag"] = buy_now_df["BuyRank"] <= 10

# Läs kapital från Parametrar
def load_params(mall_path: str) -> dict:
    try:
        dfp = pd.read_excel(mall_path, sheet_name="Parametrar")
        dfp = dfp.iloc[:, :2].copy()
        dfp.columns = ["key","value"]
        dfp["key_norm"] = dfp["key"].astype(str).str.strip().str.lower()
        return dict(zip(dfp["key_norm"], dfp["value"]))
    except Exception:
        return {}

params = load_params(MALL_PATH)
capital = 0.0
for k in ["kapital att handla för", "kapital", "kapital_att_handla_for"]:
    if k in params:
        try:
            capital = float(params[k]); break
        except Exception:
            pass

per_ticker = (capital/10.0) if capital > 0 else 0.0
buy_now_df["QtyToBuy"] = 0
if per_ticker > 0:
    m = buy_now_df["BuyRank"] <= 10
    qty = np.floor(per_ticker / buy_now_df.loc[m, "Price"].replace(0, np.nan)).fillna(0).astype(int)
    buy_now_df.loc[m, "QtyToBuy"] = qty

# ---------- Export: format & placering ----------
# Vi låter Ret_* ligga som decimaler (0.1234) och formaterar som % i Excel
# Övriga numeriska (ej QtyToBuy/Ret_*) rundas till 2 decimaler
export_df = buy_now_df.copy()
num_cols = export_df.select_dtypes(include=[np.number]).columns.tolist()
for col in num_cols:
    if col not in ["QtyToBuy", "Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
        export_df[col] = export_df[col].round(2)
export_df = export_df.sort_values("BuyRank").reset_index(drop=True)

# Kopiera mall -> skriv om ENDAST BuyNow och placera efter Calc
copyfile(MALL_PATH, OUT_PATH)
wb = load_workbook(OUT_PATH)

# Ta bort gammal BuyNow om den finns
if "BuyNow" in wb.sheetnames:
    wb.remove(wb["BuyNow"])

# Skapa BuyNow direkt efter Calc
if "Calc" not in wb.sheetnames:
    fail("Fliken 'Calc' saknas i utfilen – kan inte placera BuyNow efter Calc.")
calc_index = wb.sheetnames.index("Calc")
ws = wb.create_sheet("BuyNow", index=calc_index+1)

# Skriv header + data
headers = list(export_df.columns)
for j,h in enumerate(headers, start=1):
    ws.cell(row=1, column=j, value=h)
for i,row in export_df.iterrows():
    for j,h in enumerate(headers, start=1):
        ws.cell(row=i+2, column=j, value=row[h])

# Formatering: Ret_* som 0.00%, QtyToBuy som 0, övrigt 0.00
header_map = {h:i+1 for i,h in enumerate(headers)}

def fmt_col(name, fmt):
    col = header_map.get(name)
    if not col: return
    for r in range(2, ws.max_row+1):
        ws.cell(row=r, column=col).number_format = fmt

for c in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
    if c in header_map: fmt_col(c, "0.00%")
if "QtyToBuy" in header_map: fmt_col("QtyToBuy", "0")

for name in headers:
    if name not in {"Ret_1m","Ret_3m","Ret_6m","Ret_12m","QtyToBuy"}:
        col = header_map[name]
        for r in range(2, ws.max_row+1):
            cell = ws.cell(row=r, column=col)
            if isinstance(cell.value, (int, float)):
                cell.number_format = "0.00"

# Autofit
for idx,name in enumerate(headers, start=1):
    maxlen = len(str(name))
    for r in range(2, ws.max_row+1):
        v = ws.cell(row=r, column=idx).value
        if v is not None:
            maxlen = max(maxlen, len(str(v)))
    ws.column_dimensions[get_column_letter(idx)].width = min(maxlen + 2, 50)

wb.save(OUT_PATH)
log("[OK] Momentum.xlsx uppdaterad – BuyNow efter Calc, 15 rader, QtyToBuy för topp-10, returer korrekta.")
