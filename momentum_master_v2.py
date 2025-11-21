import os, sys, shutil, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

TEMPLATE_FILE   = "Momentum mall fil.xlsx"
OUTPUT_FILE     = "Momentum.xlsx"
BACKUP_DIR      = Path("backups")
POLYGON_API     = os.environ.get("POLYGON_API_KEY", "").strip()
TARGET_POSITIONS= 10  # lika vikt per position

def log(msg): print(msg, flush=True)
def ensure_dir(p: Path): p.mkdir(parents=True, exist_ok=True)
def today_stamp(): return dt.datetime.now().strftime("%Y%m%d")

def backup_template(src: Path):
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ','_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst}")

def get_usdsek():
    try:
        r = requests.get("https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
                         params={"adjusted":"true","limit":1,"apiKey":POLYGON_API}, timeout=6)
        r.raise_for_status()
        res = r.json().get("results", [])
        if res and res[0].get("c"): return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] polygon misslyckades: {e}")
    return 10.0

def read_param_value(path: Path, label_substr: str, default=None, numeric=True):
    try:
        df = pd.read_excel(path, sheet_name="Parametrar", header=None)
        mask = df[0].astype(str).str.lower().str.contains(label_substr.lower(), na=False)
        if mask.any():
            val = df.loc[mask, 1].iloc[0]
            if numeric:
                v = pd.to_numeric(val, errors="coerce")
                return default if pd.isna(v) else float(v)
            return str(val)
    except Exception as e:
        log(f"[WARN] Parametrar läsning '{label_substr}' misslyckades: {e}")
    return default

def norm_name(s: str) -> str:
    return ''.join(ch for ch in str(s).lower() if ch.isalnum())

def choose_column(df: pd.DataFrame, candidates: list[str], require_positive: bool=False):
    names = {c: norm_name(c) for c in df.columns}
    rev   = {v: k for k, v in names.items()}
    for key in candidates:
        if key in rev:
            col = rev[key]
            s = pd.to_numeric(df[col], errors="coerce")
            if not require_positive or s.dropna().gt(0).any():
                return col
    return None

def resolve_price_usd(df: pd.DataFrame, usdsek: float) -> tuple[pd.Series,str]:
    # 1) USD-pris
    usd_keys = ["pricenow","price","last","lastprice","close","lastclose","latest","latestprice",
                "pricelatest","pricenowusd","priceusd","price0","price_0","prisusd","senaste"]
    col_usd = choose_column(df, usd_keys, require_positive=True)
    if col_usd:
        s = pd.to_numeric(df[col_usd], errors="coerce").where(lambda x: x>0)
        if s.dropna().any():
            return s, f"[INFO] Vald pris-kolumn = {col_usd} [USD]"

    # 2) SEK-pris + FX
    sek_keys = ["pricenowsek","priceseK","price_sek","prissek","pris","pris(sek)","senastepris"]
    fx_keys  = ["fxnow","fx","usdsek","sekusd","exchangerate","rate"]
    col_sek  = choose_column(df, sek_keys, require_positive=True)
    if col_sek:
        ssek = pd.to_numeric(df[col_sek], errors="coerce").where(lambda x: x>0)
        col_fx = choose_column(df, fx_keys, require_positive=True)
        if col_fx:
            fx = pd.to_numeric(df[col_fx], errors="coerce").where(lambda x: x>0)
            susd = ssek / fx
            return susd, f"[INFO] Vald pris-kolumn = {col_sek} [SEK] → USD via {col_fx}"
        susd = ssek / max(usdsek, 1e-9)
        return susd, f"[INFO] Vald pris-kolumn = {col_sek} [SEK] → USD via Polygon({usdsek:.4f})"

    # 3) Första vettiga numeriska kolumn
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.dropna().gt(0).any():
            log(f"[WARN] Ingen tydlig pris-kolumn; använder {c}")
            return s, f"[WARN] Pris = {c} [okänd]"
    raise RuntimeError("Kunde inte härleda pris i EarlyCandidates.")

def compute_returns_if_missing(df: pd.DataFrame, price_col: str):
    """Om Ret1m/Ret3m saknas, försök skapa dem från Price_1m/Price_3m."""
    if "Ret1m" not in df.columns or df["Ret1m"].isna().all():
        p1m = choose_column(df, ["price1m","price_1m","p1m"])
        if p1m:
            df["Ret1m"] = (pd.to_numeric(df[price_col], errors="coerce") /
                           pd.to_numeric(df[p1m], errors="coerce") - 1.0) * 100.0
    if "Ret3m" not in df.columns or df["Ret3m"].isna().all():
        p3m = choose_column(df, ["price3m","price_3m","p3m"])
        if p3m:
            df["Ret3m"] = (pd.to_numeric(df[price_col], errors="coerce") /
                           pd.to_numeric(df[p3m], errors="coerce") - 1.0) * 100.0
    return df

def build_buylist_from_ec(df_ec_raw: pd.DataFrame, portfolio_value: float, usdsek: float, min_price_usd: float) -> pd.DataFrame:
    """
    Momentum från EarlyCandidates (robust):
      • Auto-pris (USD eller SEK→USD)
      • Hitta SMA50/SMA200/Ret1m/Ret3m/Score_MOMO med bred namnsök (sv/eng)
      • Beräkna Ret1m/Ret3m från Price_1m/Price_3m om behövs
      • Filter: pris ≥ min_price, (pris ≥ SMA200 om SMA200 finns), Ret1m ≥ −20
      • Rank: 0.5*Score_MOMO + 0.3*Ret1m + 0.2*Ret3m (fallback: 0.6*Ret1m + 0.4*Ret3m)
      • Top15, flagga Top10, Qty enligt Parametrar!B1
    """
    df = df_ec_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # pris
    price_usd, price_log = resolve_price_usd(df, usdsek); log(price_log)
    df["__price_usd__"] = pd.to_numeric(price_usd, errors="coerce")

    # hitta kolumner
    sma50 = choose_column(df, ["sma50","ma50","glid50","ma_50"])
    sma200= choose_column(df, ["sma200","ma200","glid200","ma_200"])
    ret1  = choose_column(df, ["ret1m","ret_1m","return1m","m1return","retm1","avkastning1m"])
    ret3  = choose_column(df, ["ret3m","ret_3m","return3m","m3return","retm3","avkastning3m"])
    score = choose_column(df, ["scoremomo","score_momo","momentumscore","momoscore","momo"])

    # numerik
    for c in [sma50, sma200, ret1, ret3, score]:
        if c:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # rensa grunddata
    df = df.replace([np.inf,-np.inf], np.nan)
    need_basic = ["Ticker","__price_usd__"]
    df = df.dropna(subset=[c for c in need_basic if c in df.columns])
    df = df[df["__price_usd__"] > 0]

    # fyll returer om saknas
    if ret1 is None or ret3 is None:
        df = compute_returns_if_missing(df, "__price_usd__")
        if ret1 is None: ret1 = "Ret1m" if "Ret1m" in df.columns else None
        if ret3 is None: ret3 = "Ret3m" if "Ret3m" in df.columns else None

    # basfilter
    df = df[df["__price_usd__"] >= float(min_price_usd)]
    if sma200:
        df = df[(df[sma200] > 0) & (df["__price_usd__"] >= df[sma200])]
    if ret1:
        df = df[df[ret1] >= -20]

    if df.empty:
        log("[WARN] Fallback: efter filter finns inga rader kvar; rankar på allt vi har.")
        df = df_ec_raw.copy()
        df["__price_usd__"], _ = resolve_price_usd(df, usdsek)
        for c in [ret1, ret3, score]:
            if c:
                df[c] = pd.to_numeric(df.get(c), errors="coerce")
        df = df.replace([np.inf,-np.inf], np.nan)
        df = df.dropna(subset=["Ticker","__price_usd__"])
        df = df[df["__price_usd__"]>0]

    # ranking
    have_score = score is not None and score in df.columns
    have_ret1  = ret1  is not None and ret1  in df.columns
    have_ret3  = ret3  is not None and ret3  in df.columns

    if have_score and have_ret1 and have_ret3:
        df["RankScore"] = 0.5*df[score] + 0.3*df[ret1] + 0.2*df[ret3]
        log(f"[INFO] Rank: 0.5*{score} + 0.3*{ret1} + 0.2*{ret3}")
    elif have_ret1 and have_ret3:
        df["RankScore"] = 0.6*df[ret1] + 0.4*df[ret3]
        log(f"[INFO] Rank fallback: 0.6*{ret1} + 0.4*{ret3}")
    elif have_score and have_ret1:
        df["RankScore"] = 0.7*df[score] + 0.3*df[ret1]
        log(f"[INFO] Rank fallback: 0.7*{score} + 0.3*{ret1}")
    elif have_score:
        df["RankScore"] = df[score]
        log(f"[INFO] Rank fallback: {score}")
    else:
        # sista utväg: sortera på pris (högst först) – bara för att alltid ge ut en lista
        df["RankScore"] = df["__price_usd__"]
        log("[INFO] Rank fallback: Price (ingen score/ret tillgänglig)")

    df = df.sort_values("RankScore", ascending=False).reset_index(drop=True)

    # toppar + qty
    df["Rank"]  = df.index + 1
    df["Top10"] = df["Rank"] <= 10
    df = df.head(15).copy()

    # sizing
    df["FX"]        = usdsek
    df["Price SEK"] = df["__price_usd__"] * usdsek
    # portföljvärde injiceras senare i main()
    return df, {"sma50":sma50, "sma200":sma200, "ret1":ret1, "ret3":ret3, "score":score}

def write_buynow(wb, df):
    old_index=None
    for i, sh in enumerate(wb.worksheets):
        if sh.title=="BuyNow":
            old_index=i
            wb.remove(sh)
            break
    ws=wb.create_sheet("BuyNow")
    for c,h in enumerate(df.columns,1): ws.cell(1,c,h)
    for r_idx,row in enumerate(df.itertuples(index=False),2):
        for c_idx,val in enumerate(row,1): ws.cell(r_idx,c_idx,val)
    for i in range(1,len(df.columns)+1):
        ws.column_dimensions[get_column_letter(i)].width=14
    if old_index is not None:
        order=wb.worksheets[:]
        new_sheet=order.pop(-1)
        order.insert(old_index,new_sheet)
        wb._sheets=order
def add_sector_momentum(df_ec):
    import pandas as pd
    import numpy as np
    from pathlib import Path

    SECTOR_MAP_FILE = Path("public/data/sector_map.csv")

    df = df_ec.copy()

    # 1. merge sektor-info
    if SECTOR_MAP_FILE.exists():
        df_sector = pd.read_csv(SECTOR_MAP_FILE).drop_duplicates(subset=["Ticker"])
        df = df.merge(df_sector[["Ticker","Sector","Industry"]], on="Ticker", how="left")
    else:
        df["Sector"] = "Unknown"
        df["Industry"] = ""

    # 2. numeriska fält
    for col in ["Score_MOMO", "Ret3m", "Ret6m"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Sector"] = df["Sector"].fillna("Unknown")

    # 3. sektorstatistik
    sector_stats = df.groupby("Sector").agg(
        SectorScore=("Score_MOMO","median"),
        SectorRet3m=("Ret3m","median"),
        SectorRet6m=("Ret6m","median")
    ).reset_index()

    df = df.merge(sector_stats, on="Sector", how="left")

    # 4. totalscore = aktie + sektorbonus
    df["TotalScore"] = (
        0.6*df["Score_MOMO"].fillna(0) +
        0.3*df["SectorScore"].fillna(0) +
        0.1*(df["SectorRet3m"].fillna(0) + df["SectorRet6m"].fillna(0))
    )

    return df

def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists(): sys.exit(f"Fel: {tpl} saknas")
    backup_template(tpl)

    portval   = read_param_value(tpl, "portföljvärde", default=0.0, numeric=True)
    min_price = read_param_value(tpl, "min pris", default=1.0, numeric=True)
    log(f"[INFO] Portföljvärde(SEK) = {portval}")
    log(f"[INFO] Min pris (USD)    = {min_price}")

    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    # === Läs EarlyCandidates (robust pipeline) ===
    df_ec = pd.read_excel(tpl, sheet_name="EarlyCandidates")
    df_buy, used = build_buylist_from_ec(df_ec, portval, usdsek, min_price)

    # qty nu när vi vet portföljvärdet
    per_pos_sek = (portval / TARGET_POSITIONS) if portval > 0 else 0.0
    def qty(sek): 
        if sek<=0 or per_pos_sek<=0: return 0
        q=int(np.floor(per_pos_sek/sek))
        return max(q,1)
    df_buy["Qty"] = [qty(v) if top else 0 for v, top in zip(df_buy["Price SEK"], df_buy["Top10"])]
    df_buy["Position SEK"] = df_buy["Qty"] * df_buy["Price SEK"]

    # kolumner att visa
    cols = ["Rank","Ticker","Top10","Qty","__price_usd__","FX","Price SEK","Position SEK","RankScore"]
    # visa gärna vad vi hittade (om de finns)
    for k in ["score","ret1","ret3","sma50","sma200"]:
        col = used.get(k)
        if col and col in df_ec.columns:
            # lägg in data kopierad in i utmatningen
            df_buy[col] = pd.to_numeric(df_ec[col], errors="coerce")
            cols.append(col)

    df_out = df_buy[cols].copy()
    df_out = df_out.rename(columns={"__price_usd__":"Price_Used_USD"})

    wb = load_workbook(tpl)
    write_buynow(wb, df_out)

    out = Path(OUTPUT_FILE)
    tmp = out.with_suffix(".tmp")
    wb.save(tmp)
    if out.exists(): out.unlink()
    tmp.replace(out)

    # logga vilka kolumner vi använde
    log(f"[INFO] Använde kolumner: Price(USD)=Price_Used_USD, SMA50={used.get('sma50')}, SMA200={used.get('sma200')}, Ret1m={used.get('ret1')}, Ret3m={used.get('ret3')}, Score={used.get('score')}")
    log(f"[OK] Momentum.xlsx klar. Kandidater: {', '.join(df_out['Ticker'].astype(str).tolist())}")

if __name__ == "__main__":
    main()
