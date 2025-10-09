# momentum_master.py
# Bygger ENDAST BuyNow enligt regler:
# - Alltid 15 aktier (Price>SMA200, Ret_3m>0, Ret_6m>0; fyll upp till 15 med bästa som åtminstone Price>SMA200)
# - QtyToBuy endast för topp 10, baserat på Parametrar["Kapital att handla för"] (lika per aktie, golvat)
# - Ret_1m–Ret_12m visas som procent med två decimaler i Excel
# - Övriga numeriska kolumner i BuyNow visas med två decimaler (QtyToBuy = heltal)
# - Universe och alla övriga mall-flikar lämnas ORÖRDA

import os
import sys
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from shutil import copyfile

# ---- Filnamn ----
MALL_PATH = "Momentum mall fil.xlsx"
OUT_PATH = "Momentum.xlsx"

def fail(msg: str):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)

# 1) Kontrollera att mallen finns
if not os.path.exists(MALL_PATH):
    fail(f"Mallen saknas: {MALL_PATH}")

# 2) Läs in flikar vi behöver ur mallen
try:
    # Calc används som underlag ("base")
    calc_df = pd.read_excel(MALL_PATH, sheet_name="Calc")
except Exception as e:
    fail(f"Kunde inte läsa fliken 'Calc' ur mallen: {e}")

# Parametrar som key/value (för kapital)
def load_params_dict(mall_path: str) -> dict:
    try:
        dfp = pd.read_excel(mall_path, sheet_name="Parametrar")
        kv = dfp.iloc[:, :2].copy()
        kv.columns = ["key", "value"]
        kv["key_norm"] = kv["key"].astype(str).strip().str.lower()
        return dict(zip(kv["key_norm"], kv["value"]))
    except Exception:
        return {}

params = load_params_dict(MALL_PATH)

# 3) Säkerställ nödvändiga kolumner i Calc
required_cols = ["Ticker", "Price", "SMA200", "Ret_3m", "Ret_6m"]
missing = [c for c in required_cols if c not in calc_df.columns]
if missing:
    fail(f"Saknade kolumner i Calc: {missing}. Kan inte bygga BuyNow.")

base = calc_df.copy()

# 4) Robust numerik och retur-decimaler internt
num_cols_to_parse = ["Price", "SMA200", "Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]
for c in num_cols_to_parse:
    if c in base.columns:
        base[c] = pd.to_numeric(base[c], errors="coerce")

for c in ["Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
    if c in base.columns:
        # Om värdet ligger som 12.34 i stället för 0.1234 -> gör om till decimal
        base[c] = base[c].where(base[c].abs() <= 1, base[c] / 100.0)

# 5) Momentum-filter (utan volymkrav)
flt_core = (
    (base["Price"] > base["SMA200"].fillna(np.inf)) &
    (base["Ret_3m"].fillna(-1) > 0) &
    (base["Ret_6m"].fillna(-1) > 0)
)
cand = base.loc[flt_core].copy()

# 6) Rankingkolumn: ScoreAdj -> Score -> MomentumScore -> Ret_6m
rank_cols = [c for c in ["ScoreAdj", "Score", "MomentumScore", "Ret_6m"] if c in base.columns]
if not rank_cols:
    fail("Ingen rankkolumn hittades (förväntade ScoreAdj/Score/MomentumScore/Ret_6m).")
rank_col = rank_cols[0]

# 7) Topp 15 ur filtret, fyll upp till 15 med Price>SMA200 om färre
top_core = cand.sort_values(rank_col, ascending=False).head(15).copy()
need = 15 - len(top_core)
if need > 0:
    trend = base.loc[(base["Price"] > base["SMA200"].fillna(np.inf))].copy()
    trend = trend[~trend["Ticker"].isin(top_core["Ticker"])]
    filler = trend.sort_values(rank_col, ascending=False).head(need)
    buy_now_df = pd.concat([top_core, filler], ignore_index=True)
else:
    buy_now_df = top_core

# 8) Säkerställ exakt 15 unika tickers
buy_now_df = buy_now_df.dropna(subset=["Ticker"]).drop_duplicates(subset=["Ticker"]).head(15).copy()

# 9) BuyRank/BuyFlag
buy_now_df.insert(0, "BuyRank", np.arange(1, len(buy_now_df) + 1))
buy_now_df["BuyFlag"] = buy_now_df["BuyRank"] <= 10

# 10) QtyToBuy för topp 10 baserat på Parametrar["Kapital att handla för"]
capital = 0.0
for k in ["kapital att handla för", "kapital", "kapital_att_handla_for"]:
    if k in params:
        try:
            capital = float(params[k]); break
        except Exception:
            pass

per_ticker_budget = (capital / 10.0) if capital > 0 else 0.0

buy_now_df["QtyToBuy"] = 0
if "Price" in buy_now_df.columns and per_ticker_budget > 0:
    mask_top10 = buy_now_df["BuyRank"] <= 10
    # floor(allokering / pris) → heltal
    qty = np.floor(per_ticker_budget / buy_now_df.loc[mask_top10, "Price"].replace(0, np.nan)).fillna(0).astype(int)
    buy_now_df.loc[mask_top10, "QtyToBuy"] = qty

# 11) Skapa exportkopia:
# - Ret_1m–Ret_12m -> procentvärden (12.34 = 12.34%)
# - Övriga numeriska -> 2 decimaler (QtyToBuy lämnas som heltal)
export_df = buy_now_df.copy()
for c in ["Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
    if c in export_df.columns:
        export_df[c] = (export_df[c] * 100).round(2)

num_cols_export = export_df.select_dtypes(include=[np.number]).columns.tolist()
for col in num_cols_export:
    if col not in ["QtyToBuy", "Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
        export_df[col] = export_df[col].round(2)

export_df = export_df.sort_values("BuyRank").reset_index(drop=True)

# 12) Kopiera mallen till utfilen (behåll alla flikar orörda) och ersätt enbart BuyNow
copyfile(MALL_PATH, OUT_PATH)

wb = load_workbook(OUT_PATH)
# Ta bort ev. befintlig BuyNow-flik för att skriva om den
if "BuyNow" in wb.sheetnames:
    ws_old = wb["BuyNow"]
    wb.remove(ws_old)
ws = wb.create_sheet("BuyNow")

# Skriv rubriker
headers = list(export_df.columns)
for j, h in enumerate(headers, start=1):
    ws.cell(row=1, column=j, value=h)

# Skriv data
for i, row in export_df.iterrows():
    for j, h in enumerate(headers, start=1):
        ws.cell(row=i+2, column=j, value=row[h])

# 13) Formatering: Ret_* = "0.00%", QtyToBuy = "0", övriga numeriska = "0.00"
header_map = {h: idx+1 for idx, h in enumerate(headers)}

def format_col_percent(name):
    col = header_map.get(name)
    if not col: return
    for r in range(2, ws.max_row + 1):
        cell = ws.cell(row=r, column=col)
        cell.number_format = "0.00%"

def format_col_two_decimals(name):
    col = header_map.get(name)
    if not col: return
    for r in range(2, ws.max_row + 1):
        cell = ws.cell(row=r, column=col)
        # formatera endast numeriska celler
        if isinstance(cell.value, (int, float)):
            cell.number_format = "0.00"

def format_col_integer(name):
    col = header_map.get(name)
    if not col: return
    for r in range(2, ws.max_row + 1):
        cell = ws.cell(row=r, column=col)
        if isinstance(cell.value, (int, float)):
            cell.number_format = "0"

# Procentkolumner
for c in ["Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m"]:
    if c in header_map:
        format_col_percent(c)

# QtyToBuy som heltal
if "QtyToBuy" in header_map:
    format_col_integer("QtyToBuy")

# Övriga numeriska -> 0.00 (exkludera procent + QtyToBuy)
exclude = {"Ret_1m", "Ret_3m", "Ret_6m", "Ret_12m", "QtyToBuy"}
for name in headers:
    if name not in exclude:
        format_col_two_decimals(name)

# (valfritt) Autofit (enkel, baserad på längsta cellinnehåll)
for col_idx, name in enumerate(headers, start=1):
    max_len = len(str(name))
    for r in range(2, ws.max_row + 1):
        val = ws.cell(row=r, column=col_idx).value
        if val is None:
            continue
        max_len = max(max_len, len(str(val)))
    ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 50)

wb.save(OUT_PATH)

print("[OK] Momentum.xlsx skapad/uppdaterad med BuyNow enligt regler.")
