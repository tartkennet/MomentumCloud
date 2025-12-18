import os
import sys
import shutil
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


# =========================
# Konfiguration
# =========================
TEMPLATE_FILE    = "Momentum mall fil.xlsx"
OUTPUT_FILE      = "Momentum.xlsx"
BACKUP_DIR       = Path("backups")
POLYGON_API_KEY  = os.environ.get("POLYGON_API_KEY", "").strip()

SECTOR_MAP_FILE  = Path("public/data/sector_map.csv")

TARGET_POSITIONS = 10  # lika vikt per position (Top10)
DEFAULT_MIN_PRICE_USD = 5.0


# =========================
# Helpers
# =========================
def log(msg: str) -> None:
    print(msg, flush=True)

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def today_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d")

def backup_template(src: Path) -> None:
    ensure_dir(BACKUP_DIR)
    dst = BACKUP_DIR / f"{src.stem.replace(' ', '_')}_{today_stamp()}.xlsx"
    shutil.copy2(src, dst)
    log(f"[BACKUP] Sparad: {dst}")

def get_usdsek() -> float:
    """
    Hämtar USD/SEK från Polygon. Returnerar 10.0 som fallback om något strular.
    """
    if not POLYGON_API_KEY:
        log("[WARN] POLYGON_API_KEY saknas – använder USDSEK=10.0 fallback")
        return 10.0

    try:
        r = requests.get(
            "https://api.polygon.io/v2/aggs/ticker/C:USDSEK/prev",
            params={"adjusted": "true", "limit": 1, "apiKey": POLYGON_API_KEY},
            timeout=10,
        )
        r.raise_for_status()
        res = r.json().get("results", [])
        if res and res[0].get("c"):
            return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] USDSEK polygon misslyckades: {e}")

    return 10.0

def read_param_value(path: Path, label_substr: str, default=None, numeric=True):
    """
    Läser Parametrar-bladet som 2 kolumner utan rubriker:
    kol A: label, kol B: värde
    """
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
    return "".join(ch for ch in str(s).lower().strip() if ch.isalnum())

def choose_column(df: pd.DataFrame, candidates: list[str], require_positive: bool=False):
    """
    Väljer kolumn i df vars normaliserade namn matchar någon kandidat.
    """
    names = {c: norm_name(c) for c in df.columns}
    rev = {}
    for k, v in names.items():
        # om krockar: behåll första
        if v not in rev:
            rev[v] = k

    for key in candidates:
        if key in rev:
            col = rev[key]
            s = pd.to_numeric(df[col], errors="coerce")
            if not require_positive:
                return col
            if s.dropna().gt(0).any():
                return col
    return None

def resolve_price_usd(df: pd.DataFrame, usdsek: float) -> tuple[pd.Series, str]:
    """
    Försöker hitta en vettig pris-kolumn i USD.
    Om bara SEK-pris finns: konvertera till USD.
    """
    # 1) Tydliga USD-kolumner
    usd_keys = [
        "pricenow", "price", "last", "lastprice", "close", "lastclose", "latest", "latestprice",
        "pricelatest", "priceusd", "pricenowusd", "price0", "price_0", "senaste"
    ]
    col_usd = choose_column(df, usd_keys, require_positive=True)
    if col_usd:
        s = pd.to_numeric(df[col_usd], errors="coerce")
        s = s.where(s > 0)
        if s.dropna().any():
            return s, f"[INFO] Vald pris-kolumn = {col_usd} [USD]"

    # 2) SEK-kolumn + ev FX
    sek_keys = ["prissek", "price_sek", "pricenowsek", "pris", "pris(sek)", "senastepris"]
    fx_keys  = ["fx", "fxnow", "usdsek", "exchangerate", "rate"]

    col_sek = choose_column(df, sek_keys, require_positive=True)
    if col_sek:
        ssek = pd.to_numeric(df[col_sek], errors="coerce").where(lambda x: x > 0)
        col_fx = choose_column(df, fx_keys, require_positive=True)
        if col_fx:
            fx = pd.to_numeric(df[col_fx], errors="coerce").where(lambda x: x > 0)
            susd = ssek / fx
            return susd, f"[INFO] Vald pris-kolumn = {col_sek} [SEK] → USD via {col_fx}"
        susd = ssek / max(usdsek, 1e-9)
        return susd, f"[INFO] Vald pris-kolumn = {col_sek} [SEK] → USD via Polygon({usdsek:.4f})"

    # 3) Sista utväg: första numeriska kolumn med positiva tal
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.dropna().gt(0).any():
            log(f"[WARN] Ingen tydlig pris-kolumn; använder {c}")
            return s, f"[WARN] Pris = {c} [okänd]"

    raise RuntimeError("Kunde inte härleda pris i EarlyCandidates.")

def compute_returns_if_missing(df: pd.DataFrame, price_col: str) -> pd.DataFrame:
    """
    Om Ret1m/Ret3m/Ret6m saknas, försök skapa dem från Price_1m/Price_3m/Price_6m.
    (procent)
    """
    def _ret_from(past_key_candidates, ret_name):
        if ret_name not in df.columns or df[ret_name].isna().all():
            past = choose_column(df, past_key_candidates, require_positive=True)
            if past:
                now = pd.to_numeric(df[price_col], errors="coerce")
                before = pd.to_numeric(df[past], errors="coerce")
                df[ret_name] = (now / before - 1.0) * 100.0

    _ret_from(["price1m","price_1m","p1m","pris1m"], "Ret1m")
    _ret_from(["price3m","price_3m","p3m","pris3m"], "Ret3m")
    _ret_from(["price6m","price_6m","p6m","pris6m"], "Ret6m")
    return df

def add_sector_momentum(df_ec: pd.DataFrame) -> pd.DataFrame:
    """
    Alternativ B:
    - Merg:a in Sector/Industry från sector_map.csv
    - Beräkna StockMomentum (viktad Ret1m/Ret3m/Ret6m)
    - Beräkna Accel (Ret1m - Ret3m)
    - Beräkna SectorMomentum som median(StockMomentum) per sektor
    - TotalScore = 0.65*StockMomentum + 0.25*z(SectorMomentum) + 0.10*Accel
    """
    df = df_ec.copy()

    # Säkerställ Ticker
    if "Ticker" not in df.columns:
        # försök hitta alternativ kolumn
        alt = choose_column(df, ["ticker","symbol"])
        if alt:
            df = df.rename(columns={alt: "Ticker"})
        else:
            raise RuntimeError("EarlyCandidates saknar kolumnen 'Ticker'.")

    # Merge sektor
    if SECTOR_MAP_FILE.exists():
        sm = pd.read_csv(SECTOR_MAP_FILE)
        if "Ticker" not in sm.columns:
            raise RuntimeError("sector_map.csv saknar kolumnen 'Ticker'")
        sm = sm.drop_duplicates(subset=["Ticker"])
        # Sector/Industry kan saknas för vissa: fyll senare
        keep_cols = [c for c in ["Ticker", "Sector", "Industry"] if c in sm.columns]
        df = df.merge(sm[keep_cols], on="Ticker", how="left")
    else:
        df["Sector"] = "Unknown"
        df["Industry"] = ""

    df["Sector"] = df.get("Sector", "Unknown").fillna("Unknown")
    df["Industry"] = df.get("Industry", "").fillna("")

    # Numerik
    for col in ["Ret1m", "Ret3m", "Ret6m", "Ret12m", "Score_MOMO"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # StockMomentum: fokus på 1–3 månader, men med 6m som stöd
    ret1 = df["Ret1m"] if "Ret1m" in df.columns else 0.0
    ret3 = df["Ret3m"] if "Ret3m" in df.columns else 0.0
    ret6 = df["Ret6m"] if "Ret6m" in df.columns else 0.0

    ret1 = pd.to_numeric(ret1, errors="coerce").fillna(0.0)
    ret3 = pd.to_numeric(ret3, errors="coerce").fillna(0.0)
    ret6 = pd.to_numeric(ret6, errors="coerce").fillna(0.0)

    df["StockMomentum"] = 0.50 * ret1 + 0.30 * ret3 + 0.20 * ret6
    df["Accel"] = ret1 - ret3  # tappar fart => negativ

    # Sektormomentum: median per sektor
    sect = (
        df.groupby("Sector", dropna=False)
          .agg(SectorMomentum=("StockMomentum", "median"))
          .reset_index()
    )
    df = df.merge(sect, on="Sector", how="left")

    # Normalisera sektor (z-score)
    smom = df["SectorMomentum"].fillna(0.0)
    if smom.std(ddof=0) > 0:
        z = (smom - smom.mean()) / smom.std(ddof=0)
    else:
        z = smom * 0.0
    df["SectorMomentumZ"] = z

    # TotalScore (ENDA ranking)
    df["TotalScore"] = (
        0.65 * df["StockMomentum"].fillna(0.0)
        + 0.25 * df["SectorMomentumZ"].fillna(0.0)
        + 0.10 * df["Accel"].fillna(0.0)
    )

    return df

def build_buylist_from_ec(df_ec_raw: pd.DataFrame, portfolio_value: float, usdsek: float, min_price_usd: float):
    """
    Bygger BuyNow:
    - Pris-identifiering + ev retur-beräkning
    - Grundfilter för att undvika "skitaktier" och dött momentum
    - Sorterar ENDAST på TotalScore
    - Top15 + Top10 flagga
    """
    df = df_ec_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Pris
    price_usd, price_log = resolve_price_usd(df, usdsek)
    log(price_log)
    df["__price_usd__"] = pd.to_numeric(price_usd, errors="coerce")

    # SMA-kolumner om de finns
    sma200 = choose_column(df, ["sma200", "ma200", "glid200", "ma_200"])

    # Rensa
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["Ticker", "__price_usd__"])
    df = df[df["__price_usd__"] > 0]

    # Om returer saknas, försök skapa
    df = compute_returns_if_missing(df, "__price_usd__")
    for col in ["Ret1m","Ret3m","Ret6m"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # TotalScore måste finnas (add_sector_momentum ska ha körts)
    if "TotalScore" not in df.columns:
        raise RuntimeError("TotalScore saknas. Kontrollera att add_sector_momentum(df_ec) körs innan build_buylist_from_ec().")

    # ===== Filter (anti-skräp + momentum-kvalitet) =====
    df = df[df["__price_usd__"] >= float(min_price_usd)]

    # Trendfilter om SMA200 finns
    if sma200 and sma200 in df.columns:
        df[sma200] = pd.to_numeric(df[sma200], errors="coerce")
        df = df[(df[sma200] > 0) & (df["__price_usd__"] >= df[sma200])]

    # Momentumfilter (för att undvika döda eftersläntrare)
    # - kräver positiv Ret3m (huvudtrend)
    # - kräver att Ret1m inte är katastrof (du vill inte köpa en kniv)
    # - kräver att Accel inte är kraftigt negativ (tappat fart)
    if "Ret3m" in df.columns:
        df = df[df["Ret3m"].fillna(-999) > 0]
    if "Ret1m" in df.columns:
        df = df[df["Ret1m"].fillna(-999) > -10]
    if "Accel" in df.columns:
        df = df[df["Accel"].fillna(-999) > -20]

    if df.empty:
        raise RuntimeError("Efter filter blev kandidatlistan tom. Sänk filter (Ret1m/Ret3m/Accel) eller kontrollera EarlyCandidates-data.")

    # ===== Sortering: ENDAST TotalScore =====
    df = df.sort_values("TotalScore", ascending=False).reset_index(drop=True)

    # Top15 / Top10
    df["Rank"] = df.index + 1
    df["Top10"] = df["Rank"] <= 10
    df = df.head(15).copy()

    # Priser i SEK
    df["FX"] = usdsek
    df["Price SEK"] = df["__price_usd__"] * usdsek

    return df

def write_buynow(wb, df_out: pd.DataFrame):
    """
    Skriver BuyNow-fliken och behåller samma plats i flikordningen som tidigare BuyNow.
    """
    old_index = None
    for i, sh in enumerate(wb.worksheets):
        if sh.title == "BuyNow":
            old_index = i
            wb.remove(sh)
            break

    ws = wb.create_sheet("BuyNow")

    # Header
    for c, h in enumerate(df_out.columns, 1):
        ws.cell(1, c, h)

    # Data
    for r_idx, row in enumerate(df_out.itertuples(index=False), 2):
        for c_idx, val in enumerate(row, 1):
            ws.cell(r_idx, c_idx, val)

    # Auto width (rimligt)
    for i, col_name in enumerate(df_out.columns, 1):
        w = 14
        if str(col_name).lower() in ("ticker",):
            w = 10
        if str(col_name).lower() in ("sector","industry"):
            w = 18
        ws.column_dimensions[get_column_letter(i)].width = w

    # Stamp så du ser att det är rätt fil
    ws["Z1"] = f"built_by=v2_sector | {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Återinsätt på samma index som tidigare
    if old_index is not None:
        order = wb.worksheets[:]
        new_sheet = order.pop(-1)
        order.insert(old_index, new_sheet)
        wb._sheets = order


# =========================
# Main
# =========================
def main():
    tpl = Path(TEMPLATE_FILE)
    if not tpl.exists():
        sys.exit(f"Fel: {tpl} saknas")

    backup_template(tpl)

    # Parametrar
    portval = read_param_value(tpl, "portföljvärde", default=0.0, numeric=True)
    min_price = read_param_value(tpl, "min pris", default=DEFAULT_MIN_PRICE_USD, numeric=True)

    log(f"[INFO] Portföljvärde(SEK) = {portval}")
    log(f"[INFO] Min pris (USD)    = {min_price}")

    usdsek = get_usdsek()
    log(f"[INFO] USDSEK = {usdsek:.5f}")

    # Läs EarlyCandidates
    log("[STEP] Läser EarlyCandidates…")
    df_ec = pd.read_excel(tpl, sheet_name="EarlyCandidates")
    df_ec.columns = [str(c).strip() for c in df_ec.columns]

    # Pris behövs för retur-beräkning om saknas
    price_usd, _ = resolve_price_usd(df_ec, usdsek)
    df_ec["__price_usd__"] = pd.to_numeric(price_usd, errors="coerce")
    df_ec = compute_returns_if_missing(df_ec, "__price_usd__")

    # Lägg på sektor + TotalScore
    log("[STEP] Beräknar sektor + TotalScore…")
    df_ec = add_sector_momentum(df_ec)

    # Bygg BuyNow
    log("[STEP] Bygger BuyNow…")
    df_buy = build_buylist_from_ec(df_ec, portval, usdsek, min_price)

    # Position sizing (Top10)
    per_pos_sek = (portval / TARGET_POSITIONS) if portval and portval > 0 else 0.0

    def qty_for(sek_price: float) -> int:
        if sek_price <= 0 or per_pos_sek <= 0:
            return 0
        q = int(np.floor(per_pos_sek / sek_price))
        return max(q, 1)

    df_buy["Qty"] = [
        qty_for(p) if top else 0
        for p, top in zip(df_buy["Price SEK"], df_buy["Top10"])
    ]
    df_buy["Position SEK"] = df_buy["Qty"] * df_buy["Price SEK"]

    # Output-kolumner (BuyNow ska vara lättläst och debuggbar)
    want = [
        "Rank","Ticker","Top10","Qty",
        "__price_usd__","FX","Price SEK","Position SEK",
        "Sector","Industry",
        "Ret1m","Ret3m","Ret6m",
        "StockMomentum","SectorMomentum","Accel","TotalScore",
    ]
    cols = [c for c in want if c in df_buy.columns]
    df_out = df_buy[cols].copy()
    df_out = df_out.rename(columns={"__price_usd__": "Price_Used_USD"})

    # Skriv Excel
    wb = load_workbook(tpl)
    write_buynow(wb, df_out)

    out = Path(OUTPUT_FILE)
    tmp = out.with_suffix(".tmp")

    log("[STEP] Skriver Momentum.xlsx…")
    wb.save(tmp)
    if out.exists():
        out.unlink()
    tmp.replace(out)

    tickers = ", ".join(df_out["Ticker"].astype(str).tolist())
    log(f"[OK] Momentum.xlsx klar. BuyNow: {tickers}")

if __name__ == "__main__":
    main()
