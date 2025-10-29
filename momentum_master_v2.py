import os
import sys
import time
import shutil
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill
from openpyxl.formatting.rule import FormulaRule

# =========================
# Konfiguration
# =========================
TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE   = "Momentum.xlsx"
BACKUP_DIR    = Path("backups")
POLYGON_API   = os.environ.get("POLYGON_API_KEY", "").strip()

# Mappning: dina rubriker i Trades -> interna namn
TRADES_RENAME_MAP = {
    "Date In":        "DateIn",
    "Ticker":         "Ticker",
    "Qty":            "Qty",
    "Entry (USD)":    "EntryUSD",
    "Stop@entry":     "StopEntry",
    "FX@entry":       "FXEntry",
    "Entry SEK":      "EntrySEK",
    "Fee@entry SEK":  "FeeEntrySEK",
    "Date Out":       "DateOut",
    "Exit (USD)":     "ExitUSD",
    "FX@exit":        "FXExit",
    "Exit SEK":       "ExitSEK",
    "Fee@exit SEK":   "FeeExitSEK",
    "P&L SEK":        "PLSEK",
    "P&L %":          "PLPercent",
}
REQUIRED_MIN = ["Ticker", "DateIn", "Qty", "EntryUSD"]

# =========================
# Hjälpfunktioner
# =========================
def log(msg: str):
    print(msg, flush=True)

def today_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def read_df(path: Path, sheet: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet)

def polygon_get(url, params=None, timeout_s=5):
    if not POLYGON_API:
        raise RuntimeError("POLYGON_API_KEY saknas i repository secrets.")
    params = dict(params or {})
    params["apiKey"] = POLYGON_API
    r = requests.get(url, params=params, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def get_usdsek() -> float:
    try:
        data = polygon_get("https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
                           {"adjusted":"true","limit":1}, 5)
        res = data.get("results", [])
        if res and res[0].get("c") is not None:
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] Misslyckades hämta USDSEK, använder fallback 10.0: {e}")
    return 10.0

def last_close_usd_fast(tickers, per_call_timeout=3, total_budget_s=12):
    """Snabb och snål pris-hämtning. Fallback None per ticker."""
    out = {t: None for t in tickers}
    start = time.time()
    for t in tickers:
        if time.time() - start > total_budget_s:
            break
        try:
            data = polygon_get(f"https://api.polygon.io/v2/aggs/ticker/{t}/prev",
                               {"adjusted":"true","limit":1}, per_call_timeout)
            res = data.get("results", [])
            if res and res[0].get("c") is not None:
                out[t] = float(res[0]["c"])
        except Exception:
            out[t] = None
    return out

def backup_template(src: Path):
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ','_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst.as_posix()}")

def save_atomic(wb, out_path: Path):
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    wb.save(tmp)
    if out_path.exists():
        out_path.unlink()
    tmp.replace(out_path)

def normalize_trades_headers(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = {c: TRADES_RENAME_MAP.get(str(c).strip(), str(c).strip()) for c in df.columns}
    return df.rename(columns=new_cols)

def coerce_dates(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    return df

def coerce_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def header_map(ws):
    return {(ws.cell(1, ci).value or "").strip(): ci for ci in range(1, ws.max_column+1)}

def find_last_data_row(ws, key_cols):
    """Sista rad med data i någon av nyckelkolumnerna (ignorerar FALSKT/False)."""
    maxrow = ws.max_row
    last = 1
    for r in range(2, maxrow+1):
        if any(ci and ws.cell(r, ci).value not in (None, "", "False", "FALSKT") for ci in key_cols):
            last = r
    return last

# =========================
# Huvudflöde
# =========================
def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        log(f"Error: Mallen saknas: {TEMPLATE_FILE}")
        sys.exit(1)

    backup_template(tpl)
    usdsek = get_usdsek()

    # ---------- Läsa parametrar (portföljvärde bara för KPI) ----------
    port_val = 0.0
    try:
        dfp = read_df(tpl, "Parametrar")
        colb = pd.to_numeric(dfp.iloc[:,1], errors="coerce").dropna()
        if not colb.empty:
            port_val = float(colb.iloc[0])
    except Exception:
        pass
    log(f"[INFO] USDSEK = {usdsek}  |  Portföljvärde(SEK) = {port_val}")

    # ---------- TRADES: läs, rensa svans, räkna P&L (totalbelopp) ----------
    log("[STEP] Läser & uppdaterar Trades…")
    skip_tr_blocks = False
    df_tr = pd.DataFrame()
    try:
        raw = read_df(tpl, "Trades")
        df_tr = normalize_trades_headers(raw.copy())
        df_tr = coerce_dates(df_tr, ["DateIn","DateOut"])
        df_tr = coerce_numeric(df_tr, [
            "Qty","EntryUSD","StopEntry","FXEntry","EntrySEK","FeeEntrySEK",
            "ExitUSD","FXExit","ExitSEK","FeeExitSEK","PLSEK","PLPercent"
        ])

        # trimma skräprader (FALSKT/False + tom ticker och tomt DateIn)
        df_tr = df_tr[~(
            (df_tr.get("Ticker","").astype(str).str.strip().isin(["","False","FALSKT"])) &
            (df_tr.get("DateIn").isna())
        )].copy()

        missing = [c for c in REQUIRED_MIN if c not in df_tr.columns]
        if missing:
            log(f"[WARN] Trades saknar obligatoriska kolumner {missing} — hoppar över Holdings/Realized.")
            skip_tr_blocks = True

        if not skip_tr_blocks:
            # Entry/Exit SEK = totalbelopp (om saknas → räkna upp)
            if "EntrySEK" not in df_tr or df_tr["EntrySEK"].isna().all():
                fx_e = df_tr.get("FXEntry", pd.Series(usdsek, index=df_tr.index)).fillna(usdsek)
                df_tr["EntrySEK"] = df_tr["EntryUSD"].fillna(0) * fx_e * df_tr["Qty"].fillna(0)
            if "ExitSEK" not in df_tr or df_tr["ExitSEK"].isna().all():
                fx_x = df_tr.get("FXExit", pd.Series(usdsek, index=df_tr.index)).fillna(usdsek)
                df_tr["ExitSEK"] = df_tr["ExitUSD"].fillna(0) * fx_x * df_tr["Qty"].fillna(0)

            fee_in  = df_tr.get("FeeEntrySEK", pd.Series(0.0, index=df_tr.index)).fillna(0.0)
            fee_out = df_tr.get("FeeExitSEK",  pd.Series(0.0, index=df_tr.index)).fillna(0.0)

            closed = df_tr["DateOut"].notna() & df_tr["ExitSEK"].notna()
            pl_total = (df_tr["ExitSEK"] - fee_out) - (df_tr["EntrySEK"] + fee_in)
            with np.errstate(divide='ignore', invalid='ignore'):
                pl_pct = np.where(df_tr["EntrySEK"] != 0, pl_total / df_tr["EntrySEK"], np.nan)

            df_tr.loc[closed, "PLSEK"] = pl_total[closed]
            df_tr.loc[closed, "PLPercent"] = pl_pct[closed]
    except Exception as e:
        log(f"[WARN] Kunde inte läsa Trades: {e}")
        skip_tr_blocks = True

    # ---------- Arbetsbok för cellvisa uppdateringar ----------
    wb = load_workbook(tpl)

    # --- Uppdatera Trades-arket in place (skriv bara P&L + formatera + rensa svans) ---
    if "Trades" in wb.sheetnames and not df_tr.empty:
        wsT = wb["Trades"]; hT = header_map(wsT)
        c_plsek = hT.get("P&L SEK"); c_plpct = hT.get("P&L %")
        c_din   = hT.get("Date In"); c_dout = hT.get("Date Out")
        c_tick  = hT.get("Ticker")
        last_row = find_last_data_row(wsT, [c_tick or 1, c_din or 1])

        if c_plsek and "PLSEK" in df_tr:
            for i, v in enumerate(df_tr["PLSEK"].fillna(""), start=2):
                if i > last_row: break
                cell = wsT.cell(i, c_plsek, float(v) if v != "" else None)
                cell.number_format = "#,##0.00"
        if c_plpct and "PLPercent" in df_tr:
            for i, v in enumerate(df_tr["PLPercent"].fillna(""), start=2):
                if i > last_row: break
                cell = wsT.cell(i, c_plpct, float(v) if v != "" else None)
                cell.number_format = "0.00%"

        # datumkolumner bredare
        if c_din:  wsT.column_dimensions[get_column_letter(c_din)].width  = 14
        if c_dout: wsT.column_dimensions[get_column_letter(c_dout)].width = 14

        # radera FALSKT/False-rader direkt under sista datarad
        if c_din:
            r = last_row + 1; guard = 0
            while r <= wsT.max_row and guard < 2000:
                v = wsT.cell(r, c_din).value
                if v in ("FALSKT","False", False):
                    wsT.delete_rows(r, 1); continue
                guard += 1; r += 1

    # ---------- HOLDINGS: skriv ENDAST öppna trades (DateOut NaN eller tom) ----------
    if "Holdings" in wb.sheetnames and not skip_tr_blocks and not df_tr.empty:
        wsH = wb["Holdings"]; hH = header_map(wsH)
        c_tic = hH.get("Ticker")
        c_qty = hH.get("Qty") or hH.get("Antal")
        c_ent = hH.get("Entry SEK") or hH.get("EntrySEK")
        c_mkt = hH.get("Market SEK") or hH.get("Marknad SEK")
        c_ps  = hH.get("P&L SEK") or hH.get("P/L SEK")
        c_pp  = hH.get("P&L %")  or hH.get("P/L %")
        c_sig = hH.get("Signal") or hH.get("SIGNAL") or hH.get("MomentumC") or hH.get("MomentumC ")

        if c_tic and c_ent:
            open_mask = (df_tr["DateOut"].isna()) | (df_tr["DateOut"] == "")
            base = df_tr.loc[open_mask, ["Ticker","Qty","EntrySEK","EntryUSD"]].copy()
            base["Ticker"] = base["Ticker"].astype(str).str.strip()
            base = base[base["Ticker"]!=""]
            uniq = base["Ticker"].dropna().unique().tolist()[:60]
            last_map = last_close_usd_fast(uniq, per_call_timeout=3, total_budget_s=12)

            # rensa alla datarader (behåll header)
            current_last = find_last_data_row(wsH, [c_tic])
            if current_last >= 2:
                wsH.delete_rows(2, current_last - 1)

            # skriv nya rader
            r = 2
            for _, row in base.iterrows():
                t = str(row["Ticker"]).strip()
                qty = float(row.get("Qty") or 0)
                entry_total = float(row.get("EntrySEK") or 0.0)
                last_usd = last_map.get(t)
                entry_usd = float(row.get("EntryUSD") or 0.0)
                px_usd = last_usd if last_usd is not None else entry_usd
                market_total = px_usd * usdsek * qty if (qty and px_usd) else None
                pl_sek = (market_total - entry_total) if (market_total is not None) else None
                pl_pct = (pl_sek / entry_total) if (pl_sek is not None and entry_total) else None

                wsH.cell(r, c_tic, t)
                if c_qty: wsH.cell(r, c_qty, qty if qty else None).number_format = "0"
                if c_ent: wsH.cell(r, c_ent, entry_total if entry_total else None).number_format = "#,##0.00"
                if c_mkt:
                    wsH.cell(r, c_mkt, market_total if market_total else None).number_format = "#,##0.00"
                if c_ps:
                    wsH.cell(r, c_ps, pl_sek if pl_sek is not None else None).number_format = "#,##0.00"
                if c_pp:
                    wsH.cell(r, c_pp, pl_pct if pl_pct is not None else None).number_format = "0.00%"
                r += 1

            end_r = r - 1
            # kolumnbredder så inga #### syns
            for col in [c_tic, c_qty, c_ent, c_mkt, c_ps, c_pp]:
                if col: wsH.column_dimensions[get_column_letter(col)].width = 14

            # färgkodning i kolumn T (Signal): HÅLL = grön, SÄLJ/STOP = röd
            if c_sig and end_r >= 2:
                rng = f"{get_column_letter(c_sig)}2:{get_column_letter(c_sig)}{end_r}"
                green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                red   = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                col_letter = get_column_letter(c_sig)
                wsH.conditional_formatting.add(rng,
                    FormulaRule(formula=[f'EXACT({col_letter}2,"HÅLL")'], fill=green))
                wsH.conditional_formatting.add(rng,
                    FormulaRule(formula=[f'OR(EXACT({col_letter}2,"SÄLJ"),EXACT({col_letter}2,"STOP"))'], fill=red))

    # ---------- EARLY: läs din EarlyCandidates och bygg filtrerad lista ----------
    log("[STEP] Bygger EarlyCandidates_filtered…")
    try:
        df_ec = read_df(tpl, "EarlyCandidates")
        # Normalisera rubriker som i din bild
        # Försök hitta fält även om % är lagrade som text
        def to_num(s):
            s = pd.to_numeric(s, errors="coerce")
            return s

        cols = {c.strip(): c for c in df_ec.columns}
        def col(name): return cols.get(name, name)

        # Fältnamn enligt din vy:
        # Ticker, Price_0, Price_1m, Price_3m, Price_6m, Price_12m, SMA50, SMA200, Ret1m, Ret3m, Ret6m, Ret12m, Score_MOMO
        for k in ["Price_0","Price_1m","Price_3m","Price_6m","Price_12m","SMA50","SMA200",
                  "Ret1m","Ret3m","Ret6m","Ret12m","Score_MOMO"]:
            if k in df_ec.columns:
                df_ec[k] = to_num(df_ec[k])

        # MomentumAccel = Ret1m - Ret3m (hantera NaN)
        if "Ret1m" in df_ec.columns and "Ret3m" in df_ec.columns:
            df_ec["MomentumAccel"] = (df_ec["Ret1m"].fillna(0) - df_ec["Ret3m"].fillna(0))
        else:
            df_ec["MomentumAccel"] = np.nan

        # EarlyFlag: Price_0 > SMA50 och Ret1m > 0 och Ret3m > -5
        df_ec["EarlyFlag"] = (
            (df_ec.get("Price_0", 0) > df_ec.get("SMA50", 0)) &
            (df_ec.get("Ret1m", 0) > 0) &
            (df_ec.get("Ret3m", 0) > -5)
        )

        # Rank: 0.8*Score_MOMO + 0.2*MomentumAccel
        df_ec["EarlyScore"] = df_ec.get("Score_MOMO", 0).fillna(0)*0.8 + df_ec["MomentumAccel"].fillna(0)*0.2

        # Filtrera & topp 40
        df_ec_f = df_ec.loc[df_ec["EarlyFlag"] == True].copy()
        df_ec_f = df_ec_f.sort_values("EarlyScore", ascending=False).head(40)

        # Skriv ny flik EarlyCandidates_filtered (ta bort om finns)
        if "EarlyCandidates_filtered" in wb.sheetnames:
            ws_old = wb["EarlyCandidates_filtered"]
            wb.remove(ws_old)
        wsE = wb.create_sheet("EarlyCandidates_filtered")

        headers = ["Ticker","Price_0","SMA50","SMA200","Ret1m","Ret3m","MomentumAccel","Score_MOMO","EarlyScore"]
        for c_idx, h in enumerate(headers, start=1):
            wsE.cell(1, c_idx, h)
        r = 2
        for _, row in df_ec_f.iterrows():
            wsE.cell(r, 1, str(row.get("Ticker")))
            wsE.cell(r, 2, row.get("Price_0"))
            wsE.cell(r, 3, row.get("SMA50"))
            wsE.cell(r, 4, row.get("SMA200"))
            wsE.cell(r, 5, row.get("Ret1m"))
            wsE.cell(r, 6, row.get("Ret3m"))
            wsE.cell(r, 7, row.get("MomentumAccel"))
            wsE.cell(r, 8, row.get("Score_MOMO"))
            wsE.cell(r, 9, row.get("EarlyScore"))
            r += 1

        # enkla bredder
        for i in range(1, 10):
            wsE.column_dimensions[get_column_letter(i)].width = 14

        # Trend health sammanfattning
        try:
            n = len(df_ec.index)
            if n > 0:
                gt20  = float((df_ec.get("Price_0",0) > df_ec.get("SMA50",0)/ (df_ec.get("SMA50",0)/df_ec.get("SMA50",0))).sum()) # placeholder noop
        except Exception:
            pass

        # Lägg trend health i Review
        if "Review" in wb.sheetnames:
            wsR = wb["Review"]
            # räkna andelar
            total = max(1, len(df_ec.index))
            pct20 = float(((df_ec.get("Price_0",0) > df_ec.get("SMA20", df_ec.get("SMA50",0))) ).sum() / total) if "SMA20" in df_ec.columns else np.nan
            pct50 = float(((df_ec.get("Price_0",0) > df_ec.get("SMA50",0)) ).sum() / total)
            pct200 = float(((df_ec.get("Price_0",0) > df_ec.get("SMA200",0)) ).sum() / total)

            # skriv ett litet block i högerdelen (t.ex. kol N)
            base_col = 14  # N
            wsR.cell(2, base_col, "Trend health (EarlyCandidates)")
            wsR.cell(3, base_col, ">SMA20");  wsR.cell(3, base_col+1, pct20).number_format = "0.0%"
            wsR.cell(4, base_col, ">SMA50");  wsR.cell(4, base_col+1, pct50).number_format = "0.0%"
            wsR.cell(5, base_col, ">SMA200"); wsR.cell(5, base_col+1, pct200).number_format = "0.0%"

            for c in range(base_col, base_col+2):
                wsR.column_dimensions[get_column_letter(c)].width = 16

    except Exception as e:
        log(f"[WARN] EarlyCandidates kunde inte bearbetas: {e}")

    # ---------- Flikordning: BuyNow -> Trades -> Holdings ----------
    try:
        names = wb.sheetnames[:]
        if "BuyNow" in names and "Trades" in names:
            names.remove("Trades"); names.insert(names.index("BuyNow")+1, "Trades")
        if "Holdings" in names:
            names.remove("Holdings"); names.insert(names.index("Trades")+1, "Holdings")
        wb._sheets = [wb[n] for n in names]
    except Exception:
        pass

    # ---------- Spara ----------
    log("[STEP] Skriver utdata till Excel…")
    save_atomic(wb, Path(OUTPUT_FILE))
    log("[OK] Momentum.xlsx uppdaterad — Trades/Holdings fixade, EarlyCandidates_filtered skapad, Review fått Trend health.")
    

if __name__ == "__main__":
    main()
