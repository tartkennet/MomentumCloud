# momentum_master_v3.py
# - Läser "Momentum mall fil.xlsx"
# - BACKUP till backups/Momentum_mall_YYYYMMDD.xlsx
# - BuyNow utan tomrader + smalare bredder
# - Trades (svenska rubriker; tål Fee@entry SEK / Fee@exit SEK)
#   * Uppdaterar i UT-fILEN "Momentum.xlsx": kol N (P&L SEK), kol O (P&L %) per rad
# - Holdings = öppna rader (Date Out tom)
# - Realized = stängda rader (Date Out ifylld – även om datum inte parsas exakt)
# - Review_KPI (live)
# - Review & Metrics: månatlig portföljavkastning (utan index), Sharpe/Sortino
#   * Vi fyller endast datafält; ändrar inte din layout i övrigt

import os, sys, datetime
import numpy as np
import pandas as pd
from shutil import copyfile
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import requests

MALL_PATH   = "Momentum mall fil.xlsx"
OUT_PATH    = "Momentum.xlsx"
BACKUP_DIR  = "backups"
EXCLUDE_TICKERS = {"WOLF"}

def log(m): print(m, flush=True)
def fail(m): print(f"Error: {m}", file=sys.stderr, flush=True); sys.exit(1)

def to_num_series(s: pd.Series) -> pd.Series:
    if getattr(s, "dtype", None) is not None and s.dtype.kind in "biufc":
        return pd.to_numeric(s, errors="coerce")
    x = pd.Series(s, dtype="object").astype(str).str.strip()
    x = x.str.replace("%","",regex=False).str.replace("\u00A0","",regex=False).str.replace(" ","",regex=False)
    x = x.str.replace(",",".",regex=False)
    return pd.to_numeric(x, errors="coerce")

def parse_float(v):
    try: return float(str(v).replace("\u00A0","").replace(" ","").replace(",","."))
    except: return None

def set_nice_widths(ws, default=12, narrow_pct_cols=None):
    if narrow_pct_cols is None: narrow_pct_cols = []
    for i, cell in enumerate(ws[1], start=1):
        header = str(cell.value or "")
        width = default
        if header in narrow_pct_cols or header.startswith("Ret"):
            width = 10
        if header in ("Ticker","Orsak","Signal"):
            width = 14
        ws.column_dimensions[get_column_letter(i)].width = width

# ---------- 0) Backup ----------
os.makedirs(BACKUP_DIR, exist_ok=True)
stamp = datetime.datetime.utcnow().strftime("%Y%m%d")
backup_path = os.path.join(BACKUP_DIR, f"Momentum_mall_{stamp}.xlsx")
if os.path.exists(MALL_PATH):
    copyfile(MALL_PATH, backup_path)
    log(f"[BACKUP] Sparad: {backup_path}")

if not os.path.exists(MALL_PATH): fail(f"Mallen saknas: {MALL_PATH}")

# ---------- 1) Läs Calc ----------
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

rank_col = None
for c in ["Score_MOMO","ScoreAdj","Score","MomentumScore","Ret_6m","Ret_3m"]:
    if c in calc.columns:
        work[c] = to_num_series(calc[c]); rank_col = c; break
if rank_col is None: rank_col = "Price"

# ---------- 2) Bygg BuyNow ----------
excl = work["Ticker"].str.upper().isin({t.upper() for t in EXCLUDE_TICKERS})
flt  = (work["Price"] > work["SMA200"].replace({np.nan: np.inf}))
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

# ---------- 3) Parametrar & USDSEK ----------
def read_b1_number(xlsx_path):
    try:
        df = pd.read_excel(xlsx_path, sheet_name="Parametrar", header=None)
        return parse_float(df.iat[0,1]) or 0.0  # B1
    except Exception:
        return 0.0
portfolio_value = read_b1_number(MALL_PATH)
log(f"[INFO] Portföljvärde(SEK) = {portfolio_value}")

def fetch_usdsek(default=11.0):
    api = os.getenv("POLYGON_API_KEY","").strip()
    if not api:
        log("[WARN] POLYGON_API_KEY saknas – fallback USDSEK.")
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
usdsek, usd_src = fetch_usdsek(11.0)
log(f"[INFO] USDSEK = {usdsek} ({usd_src})")

# ---------- 4) QtyToBuy (topp-10) ----------
per_ticker_budget_sek = (portfolio_value/10.0) if portfolio_value and portfolio_value>0 else 0.0
buy_now["QtyToBuy"] = 0
if per_ticker_budget_sek>0 and usdsek>0:
    m = buy_now["BuyRank"]<=10
    price_sek = buy_now.loc[m,"Price"] * usdsek
    qty = np.floor(per_ticker_budget_sek / price_sek.replace(0,np.nan)).fillna(0).astype(int)
    buy_now.loc[m,"QtyToBuy"] = qty

# ---------- 5) Läs Trades (svenska rubriker, robust Date Out) ----------
xl = pd.ExcelFile(MALL_PATH)
tr_raw = pd.read_excel(MALL_PATH, sheet_name="Trades") if "Trades" in xl.sheet_names else pd.DataFrame()

def pick(df, names):
    cols = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in cols: return cols[n.lower()]
    return None

trades = pd.DataFrame()
if not tr_raw.empty:
    col_in    = pick(tr_raw, ["Date In","Datum In","DateIn"])
    col_tkr   = pick(tr_raw, ["Ticker"])
    col_qty   = pick(tr_raw, ["Qty","Quantity","Antal"])
    col_eusd  = pick(tr_raw, ["Entry (USD)","Entry USD","EntryUSD","Pris USD","PriceUSD"])
    col_stop  = pick(tr_raw, ["Stop@entry","Stop","StopLoss"])
    col_fx_in = pick(tr_raw, ["FX@entry","FX entry","FX@in","FXin","USDSEK in"])
    col_feein = pick(tr_raw, ["Fee@entry SEK","Fee@entry","Fees@entry","Avgift in","FeesSEK in","Courtage@entry","CourtageSEK@entry"])
    col_out   = pick(tr_raw, ["Date Out","Datum Out","DateOut"])
    col_xusd  = pick(tr_raw, ["Exit (USD)","Exit USD","ExitUSD"])
    col_fx_ex = pick(tr_raw, ["FX@exit","FX exit","FX@out","FXout","USDSEK out"])
    col_feeex = pick(tr_raw, ["Fee@exit SEK","Fee@exit","Fees@exit","Avgift ut","FeesSEK out","Courtage@exit","CourtageSEK@exit"])

    need = [col_in, col_tkr, col_qty, col_eusd, col_fx_in]
    if any(c is None for c in need):
        log("[WARN] Trades saknar obligatoriska kolumner — hoppar över Holdings/Realized/Trades-P&L.")
        trades = pd.DataFrame()
    else:
        out_raw = tr_raw[col_out].astype(str) if col_out else pd.Series([], dtype=str)
        date_out_parsed = pd.to_datetime(tr_raw[col_out], errors="coerce") if col_out else pd.NaT
        trades = pd.DataFrame({
            "DateIn": pd.to_datetime(tr_raw[col_in], errors="coerce"),
            "Ticker": tr_raw[col_tkr].astype(str).str.upper().str.strip(),
            "Qty": to_num_series(tr_raw[col_qty]).fillna(0).astype(int),
            "EntryUSD": to_num_series(tr_raw[col_eusd]).fillna(0.0),
            "StopAtEntry": tr_raw[col_stop] if col_stop else np.nan,
            "FXin": to_num_series(tr_raw[col_fx_in]).fillna(usdsek),
            "FeeIn": to_num_series(tr_raw[col_feein]).fillna(0.0) if col_feein else 0.0,
            "DateOut": date_out_parsed,
            "DateOut_raw": out_raw if col_out else "",
            "ExitUSD": to_num_series(tr_raw[col_xusd]).fillna(0.0) if col_xusd else 0.0,
            "FXout": to_num_series(tr_raw[col_fx_ex]).fillna(usdsek) if col_fx_ex else usdsek,
            "FeeOut": to_num_series(tr_raw[col_feeex]).fillna(0.0) if col_feeex else 0.0,
        }).dropna(subset=["DateIn","Ticker"]).sort_values(["DateIn","Ticker"]).reset_index(drop=True)

# ---------- 6) Bygg Holdings, Realized + beräkna Trades P&L (N, O) ----------
holdings_df = None
realized_df = None
trades_pl = None   # för att skriva tillbaka N/O i utfilen

if not trades.empty:
    is_closed = (~trades["DateOut"].isna()) | (trades.get("DateOut_raw","").astype(str).str.strip() != "")
    open_mask = ~is_closed
    open_tr = trades.loc[open_mask].copy()
    closed  = trades.loc[~open_mask].copy()

    price_now = dict(zip(work["Ticker"], work["Price"]))
    ret1 = dict(zip(work["Ticker"], work.get("Ret_1m", pd.Series(dtype=float))))
    ret3 = dict(zip(work["Ticker"], work.get("Ret_3m", pd.Series(dtype=float))))
    ret6 = dict(zip(work["Ticker"], work.get("Ret_6m", pd.Series(dtype=float))))
    ret12= dict(zip(work["Ticker"], work.get("Ret_12m", pd.Series(dtype=float))))

    # Holdings: en rad per öppen trade
    rows = []
    for _, r in open_tr.iterrows():
        tkr = r["Ticker"]; qty = int(r["Qty"])
        entry_tot = qty * float(r["EntryUSD"]) * float(r["FXin"]) + float(r["FeeIn"])
        px_now = float(price_now.get(tkr, 0.0)); fx_now = float(usdsek)
        value_sek = qty * px_now * fx_now
        pnl_sek = value_sek - entry_tot
        pnl_pct = pnl_sek / entry_tot if entry_tot>0 else 0.0
        rows.append({
            "Ticker": tkr, "Qty": qty, "Date": r["DateIn"].date().isoformat(),
            "Entry SEK (tot)": round(entry_tot, 2),
            "Price now": round(px_now, 2), "FX now": round(fx_now, 2),
            "Value SEK": round(value_sek, 2), "P&L SEK": round(pnl_sek, 2), "P&L %": pnl_pct,
            "StopLoss (USD)": r["StopAtEntry"] if pd.notna(r["StopAtEntry"]) else "",
            "Ret1m": ret1.get(tkr, np.nan), "Ret3m": ret3.get(tkr, np.nan),
            "Ret6m": ret6.get(tkr, np.nan), "Ret12m": ret12.get(tkr, np.nan),
            "Score": "","FundOK":"","TrendOK":"","KÖP?":"","MomentumOK":"","Signal":"","Orsak":""
        })
    holdings_df = pd.DataFrame(rows)

    # Realized + Trades P&L
    rows_c = []; pl_rows = []
    for _, r in closed.iterrows():
        tkr = r["Ticker"]; qty = int(r["Qty"])
        entry_tot = qty * float(r["EntryUSD"]) * float(r["FXin"]) + float(r["FeeIn"])
        exit_tot  = qty * float(r["ExitUSD"])  * float(r["FXout"]) + float(r["FeeOut"])
        pnl = exit_tot - entry_tot
        pnl_pct = pnl/entry_tot if entry_tot>0 else 0.0
        if pd.notna(r["DateOut"]):
            date_out_str = r["DateOut"].date().isoformat(); month = r["DateOut"].strftime("%Y-%m")
        else:
            raw = str(r.get("DateOut_raw","")).strip()
            date_out_str = raw; month = r["DateIn"].strftime("%Y-%m")
        rows_c.append({
            "Date In": r["DateIn"].date().isoformat(), "Date Out": date_out_str, "Ticker": tkr, "Qty": qty,
            "Entry SEK (tot)": round(entry_tot,2), "Exit SEK (tot)": round(exit_tot,2),
            "Fees SEK (sum)": round(float(r["FeeIn"])+float(r["FeeOut"]),2),
            "Realized P&L SEK": round(pnl,2), "Realized P&L %": pnl_pct, "Month": month
        })
        pl_rows.append({
            "DateIn": r["DateIn"], "Ticker": tkr, "P&L_SEK": round(pnl,2), "P&L_Pct": pnl_pct
        })
    realized_df = pd.DataFrame(rows_c)
    trades_pl   = pd.DataFrame(pl_rows)

# ---------- 7) Skriv utfil ----------
copyfile(MALL_PATH, OUT_PATH)
wb = load_workbook(OUT_PATH)

# --- BuyNow (efter Calc) ---
if "BuyNow" in wb.sheetnames: wb.remove(wb["BuyNow"])
if "Calc" not in wb.sheetnames: fail("Calc saknas i utfilen.")
calc_idx = wb.sheetnames.index("Calc")
ws_bn = wb.create_sheet("BuyNow", index=calc_idx+1)

bn = buy_now.sort_values("BuyRank").reset_index(drop=True).copy()
num_cols = bn.select_dtypes(include=[np.number]).columns.tolist()
for c in num_cols:
    if c not in ["QtyToBuy","Ret_1m","Ret_3m","Ret_6m","Ret_12m"]:
        bn[c] = bn[c].round(2)
headers = list(bn.columns)
for j,h in enumerate(headers,1): ws_bn.cell(row=1,column=j,value=h)
for i,row in bn.iterrows():
    for j,h in enumerate(headers,1):
        ws_bn.cell(row=i+2,column=j,value=row[h])
hdr = {h:i+1 for i,h in enumerate(headers)}
def fmt(ws, col, fmt):
    if col not in hdr: return
    c = hdr[col]
    for r in range(2, ws.max_row+1):
        ws.cell(row=r, column=c).number_format = fmt
for c in ["Ret_1m","Ret_3m","Ret_6m","Ret_12m"]: fmt(ws_bn, c, "0.00%")
if "QtyToBuy" in hdr: fmt(ws_bn, "QtyToBuy", "0")
for name in headers:
    if name not in {"Ret_1m","Ret_3m","Ret_6m","Ret_12m","QtyToBuy"}:
        c = hdr[name]
        for r in range(2, ws_bn.max_row+1):
            cell = ws_bn.cell(row=r, column=c)
            if isinstance(cell.value, (int,float)):
                cell.number_format = "0.00"
set_nice_widths(ws_bn, default=12, narrow_pct_cols=["P&L %"])

# --- Holdings ---
if holdings_df is not None:
    if "Holdings" in wb.sheetnames: wb.remove(wb["Holdings"])
    ws_h = wb.create_sheet("Holdings")
    cols = ["Ticker","Qty","Date","Entry SEK (tot)","Price now","FX now",
            "Value SEK","P&L SEK","P&L %","StopLoss (USD)","Ret1m","Ret3m","Ret6m","Ret12m",
            "Score","FundOK","TrendOK","KÖP?","MomentumOK","Signal","Orsak"]
    for j,h in enumerate(cols,1): ws_h.cell(row=1,column=j,value=h)
    total_value,total_pnl,denom = 0.0,0.0,0.0
    for i,row in holdings_df.iterrows():
        for j,h in enumerate(cols,1):
            v = row[h] if h in row else ""
            ws_h.cell(row=i+2,column=j,value=v)
        total_value += float(row["Value SEK"]); total_pnl += float(row["P&L SEK"])
        denom += float(row["Entry SEK (tot)"])
    rtot = holdings_df.shape[0] + 2
    ws_h.cell(row=rtot, column=1, value="Totalt")
    ws_h.cell(row=rtot, column=7, value=round(total_value,2))
    ws_h.cell(row=rtot, column=8, value=round(total_pnl,2))
    pct = (total_pnl / denom) if denom>0 else 0.0
    ws_h.cell(row=rtot, column=9, value=pct)
    hdr_h = {h:i+1 for i,h in enumerate(cols)}
    def f_h(col, fmt):
        c = hdr_h[col]
        for r in range(2, ws_h.max_row+1):
            ws_h.cell(row=r, column=c).number_format = fmt
    for nm in ["Entry SEK (tot)","Value SEK","P&L SEK","Price now"]: f_h(nm, "0.00")
    f_h("FX now", "0.00")
    for nm in ["P&L %","Ret1m","Ret3m","Ret6m","Ret12m"]: f_h(nm, "0.00%")
    set_nice_widths(ws_h, default=12, narrow_pct_cols=["P&L %","Ret1m","Ret3m","Ret6m","Ret12m"])

# --- Realized ---
if realized_df is not None:
    if "Realized" in wb.sheetnames: wb.remove(wb["Realized"])
    ws_r = wb.create_sheet("Realized")
    cols_r = ["Date In","Date Out","Ticker","Qty","Entry SEK (tot)","Exit SEK (tot)",
              "Fees SEK (sum)","Realized P&L SEK","Realized P&L %","Month"]
    for j,h in enumerate(cols_r,1): ws_r.cell(row=1,column=j,value=h)
    for i,row in realized_df.iterrows():
        for j,h in enumerate(cols_r,1):
            ws_r.cell(row=i+2,column=j,value=row[h])
    hdr_r = {h:i+1 for i,h in enumerate(cols_r)}
    def f_r(col, fmt):
        c = hdr_r[col]
        for r in range(2, ws_r.max_row+1):
            ws_r.cell(row=r, column=c).number_format = fmt
    for nm in ["Entry SEK (tot)","Exit SEK (tot)","Fees SEK (sum)","Realized P&L SEK"]: f_r(nm, "0.00")
    f_r("Realized P&L %","0.00%")
    set_nice_widths(ws_r, default=12, narrow_pct_cols=["Realized P&L %"])

# --- Trades: skriv P&L till kolumn N (P&L SEK) och O (P&L %) i utfilen ---
try:
    if "Trades" in wb.sheetnames and trades_pl is not None and not trades_pl.empty:
        ws_t = wb["Trades"]
        # anta headers på rad 1, och att N=14, O=15 (0-index +1)
        # försök hitta kolumnindex via rubriker om möjligt
        headers = [str(ws_t.cell(row=1, column=c).value or "").strip() for c in range(1, ws_t.max_column+1)]
        try:
            col_pl_sek = headers.index("P&L SEK")+1
            col_pl_pct = headers.index("P&L %")+1
        except ValueError:
            # fallback på N=14, O=15
            col_pl_sek, col_pl_pct = 14, 15
        # bygg en lookup (DateIn+Ticker) -> värden
        key2pl = {(r["DateIn"].date().isoformat(), r["Ticker"]):(r["P&L_SEK"], r["P&L_Pct"]) for _,r in trades_pl.iterrows()}
        # gå igenom rader i bladet och skriv där det finns match
        for r in range(2, ws_t.max_row+1):
            d = ws_t.cell(row=r, column=1).value  # Date In
            t = ws_t.cell(row=r, column=2).value  # Ticker
            if not d or not t: continue
            try:
                dkey = pd.to_datetime(d).date().isoformat()
            except Exception:
                dkey = str(d).strip()
            tkey = str(t).strip().upper()
            if (dkey, tkey) in key2pl:
                pl_sek, pl_pct = key2pl[(dkey, tkey)]
                ws_t.cell(row=r, column=col_pl_sek, value=pl_sek).number_format = "0.00"
                ws_t.cell(row=r, column=col_pl_pct, value=pl_pct).number_format = "0.00%"
except Exception as e:
    log(f"[WARN] Kunde inte skriva P&L till Trades: {e}")

# --- Review_KPI (live) ---
if "Review_KPI" in wb.sheetnames: wb.remove(wb["Review_KPI"])
ws_k = wb.create_sheet("Review_KPI")
ws_k.cell(row=1, column=1, value="Portfolio % (live)")
ws_k.cell(row=2, column=1, value="Equity SEK (live)")
ws_k.cell(row=3, column=1, value="Realized P&L SEK (tot)")
ws_k.cell(row=4, column=1, value="Unrealized P&L SEK (nu)")
ws_k.cell(row=5, column=1, value="Value SEK (nu)")
ws_k.cell(row=6, column=1, value="Bas (Parametrar!B1)")

value_now = float(holdings_df["Value SEK"].sum()) if (holdings_df is not None and not holdings_df.empty) else 0.0
unreal_now = float(holdings_df["P&L SEK"].sum())   if (holdings_df is not None and not holdings_df.empty) else 0.0
realized_tot = float(realized_df["Realized P&L SEK"].sum()) if (realized_df is not None and not realized_df.empty) else 0.0
equity_live = value_now + realized_tot
port_pct_live = (equity_live / portfolio_value - 1.0) if portfolio_value>0 else 0.0

ws_k.cell(row=1, column=2, value=port_pct_live).number_format = "0.00%"
for r,v in [(2,equity_live),(3,realized_tot),(4,unreal_now),(5,value_now),(6,portfolio_value)]:
    ws_k.cell(row=r, column=2, value=round(v,2)).number_format = "0.00"

# --- Review & Metrics: enkel månadsserie av portfölj % ---
# Vi bygger en månads-TS: för varje månad = (sum Realized i mån + delta i Unrealized mot föreg. mån) / bas
# Enkel metod: equity_end(month)/equity_start(prev_month) - 1
try:
    # equity per datum: antag att DateIn/DateOut är handelsdagar. Vi tar equity_end idag = equity_live
    # Skapa equity per månad baserat på Realized (Month) + slutliga current value
    eq_month = {}
    if realized_df is not None and not realized_df.empty:
        for _,r in realized_df.iterrows():
            m = r["Month"]
            eq_month[m] = eq_month.get(m, 0.0) + float(r["Realized P&L SEK"])
    # Lägg till "nuvarande värde" på aktuell månad för att få en rimlig approx
    cur_m = datetime.datetime.utcnow().strftime("%Y-%m")
    eq_month[cur_m] = eq_month.get(cur_m, 0.0) + value_now  # approximation

    months_sorted = sorted(eq_month.keys())
    # ackumulera till equity
    equity = 0.0
    monthly_ret = []
    prev_equity = portfolio_value if portfolio_value>0 else 1.0
    for m in months_sorted:
        equity = portfolio_value + sum(eq_month[k] for k in months_sorted if k <= m)  # grov approximation
        ret = (equity / prev_equity) - 1.0 if prev_equity>0 else 0.0
        monthly_ret.append((m, ret))
        prev_equity = equity

    # Skriv till Review (om bladet finns): fyll kolumn B "Portfölj %"
    if "Review" in wb.sheetnames and monthly_ret:
        ws_rev = wb["Review"]
        # leta rubrikrad (hitta "Månad" i kol A och "Portfölj %" i kol B)
        # skriv från rad 2 neråt
        row = 2
        for m,ret in monthly_ret[-24:]:  # max 24 rader
            ws_rev.cell(row=row, column=1, value=m)
            ws_rev.cell(row=row, column=2, value=ret).number_format = "0.00%"
            row += 1

    # Skriv till Metrics: samma serie, lägg i kol B (Portfölj %), kol A (Månad)
    if "Metrics" in wb.sheetnames and monthly_ret:
        ws_met = wb["Metrics"]
        row = 2
        for m,ret in monthly_ret[-24:]:
            ws_met.cell(row=row, column=1, value=m)
            ws_met.cell(row=row, column=2, value=ret).number_format = "0.00%"
            row += 1

        # Sharpe/Sortino (enkel): antag rf=0, årligfaktor=sqrt(12)
        rets = np.array([r for _,r in monthly_ret[-24:]], dtype=float)
        if rets.size>1:
            mean_m = np.nanmean(rets); std_m = np.nanstd(rets, ddof=1)
            downside = np.sqrt(np.nanmean(np.minimum(rets,0.0)**2))
            sharpe  = (mean_m/ (std_m if std_m>0 else np.nan)) * np.sqrt(12) if std_m>0 else 0.0
            sortino = (mean_m/ (downside if downside>0 else np.nan)) * np.sqrt(12) if downside>0 else 0.0
        else:
            sharpe=sortino=0.0
        # skriv rubriker om tomt
        if not ws_met.cell(row=1, column=5).value: ws_met.cell(row=1, column=5, value="Sharpe")
        if not ws_met.cell(row=1, column=6).value: ws_met.cell(row=1, column=6, value="Sortino")
        ws_met.cell(row=2, column=5, value=sharpe).number_format = "0.00"
        ws_met.cell(row=2, column=6, value=sortino).number_format = "0.00"
except Exception as e:
    log(f"[WARN] Review/Metrics uppdatering misslyckades (ignorerar): {e}")

wb.save(OUT_PATH)
log("[OK] Momentum.xlsx uppdaterad — BuyNow, Trades P&L (N/O), Holdings, Realized, Review_KPI, Review & Metrics.")
