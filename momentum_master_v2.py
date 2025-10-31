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


TEMPLATE_FILE = "Momentum mall fil.xlsx"
OUTPUT_FILE = "Momentum.xlsx"
BACKUP_DIR = Path("backups")
POLYGON_API = os.environ.get("POLYGON_API_KEY", "").strip()
TARGET_POSITIONS = 10


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
                         params={"adjusted": "true", "limit": 1, "apiKey": POLYGON_API},
                         timeout=5)
        r.raise_for_status()
        d = r.json()
        res = d.get("results", [])
        if res and res[0].get("c"): return float(res[0]["c"])
    except Exception as e:
        log(f"[WARN] polygon misslyckades: {e}")
    return 10.0


def read_portfolio_value(path: Path) -> float:
    """Läs 'Portföljvärde' ur kolumn A i Parametrar-fliken."""
    try:
        df = pd.read_excel(path, sheet_name="Parametrar", header=None)
        mask = df[0].astype(str).str.lower().str.contains("portföljvärde", na=False)
        if mask.any():
            val = pd.to_numeric(df.loc[mask, 1], errors="coerce").dropna()
            if not val.empty:
                return float(val.iloc[0])
    except Exception as e:
        log(f"[WARN] Portföljvärde kunde ej läsas: {e}")
    return 0.0


def build_buylist(df_ec, portfolio_value, usdsek):
    df = df_ec.copy()
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="ignore")
    df = df.rename(columns=lambda x: x.strip())

    needed = ["Ticker","Price_0","SMA50","SMA200","Ret1m","Ret3m","Score_MOMO"]
    for n in needed:
        if n not in df.columns: raise RuntimeError(f"Saknar kolumn {n}")

    df = df[df["Price_0"]>0].copy()

    df["MomentumAccel"]=df["Ret1m"]-df["Ret3m"]
    df["Sig_StrongTrend"]=(
        (df["Price_0"]>df["SMA200"])&
        (df["SMA50"]>df["SMA200"])&
        (df["Ret3m"]>10)
    )
    df["Sig_PullbackOK"]=(
        (df["Price_0"]>df["SMA50"])&
        (df["Ret3m"]>0)&
        (df["Ret1m"].between(-5,10))
    )
    df["HasSignal"]=df["Sig_StrongTrend"]|df["Sig_PullbackOK"]

    f=df[df["HasSignal"]].copy()
    if f.empty: f=df.copy()

    f["RankScore"]=0.5*f["MomentumAccel"]+0.5*f["Ret3m"]
    f=f.sort_values("RankScore",ascending=False).head(15).reset_index(drop=True)
    f["Rank"]=f.index+1
    f["Top10"]=f["Rank"]<=10

    per_pos=portfolio_value/TARGET_POSITIONS if portfolio_value>0 else 0
    f["FX"]=usdsek
    f["Price SEK"]=f["Price_0"]*usdsek
    f["Qty"]=np.where(
        f["Top10"],
        np.maximum((per_pos/f["Price SEK"]).fillna(0).astype(int),1),
        0
    )
    f["Position SEK"]=f["Qty"]*f["Price SEK"]

    return f[["Rank","Ticker","Top10","Qty","Price_0","FX","Price SEK","Position SEK",
              "Score_MOMO","Ret1m","Ret3m","MomentumAccel","RankScore",
              "Sig_StrongTrend","Sig_PullbackOK"]]


def write_buynow(wb,df):
    old_idx=None
    for i,sh in enumerate(wb.worksheets):
        if sh.title=="BuyNow": old_idx=i; wb.remove(sh)
    ws=wb.create_sheet("BuyNow")
    for c,h in enumerate(df.columns,1): ws.cell(1,c,h)
    for r,row in enumerate(df.itertuples(index=False),2):
        for c,v in enumerate(row,1): ws.cell(r,c,v)
    for i in range(1,len(df.columns)+1):
        ws.column_dimensions[get_column_letter(i)].width=14
    if old_idx is not None:
        new_order=wb.worksheets[:]; sh=new_order.pop(-1); new_order.insert(old_idx,sh); wb._sheets=new_order


def main():
    tpl=Path(TEMPLATE_FILE)
    if not tpl.exists(): sys.exit(f"Fel: {tpl} saknas")
    backup_template(tpl)
    pv=read_portfolio_value(tpl)
    log(f"[INFO] Portföljvärde(SEK)={pv}")
    usdsek=get_usdsek(); log(f"[INFO] USDSEK={usdsek}")
    df_ec=pd.read_excel(tpl,sheet_name="EarlyCandidates")
    df_buy=build_buylist(df_ec,pv,usdsek)
    wb=load_workbook(tpl)
    write_buynow(wb,df_buy)
    out=Path(OUTPUT_FILE)
    tmp=out.with_suffix(".tmp")
    wb.save(tmp)
    if out.exists(): out.unlink()
    tmp.replace(out)
    log("[OK] Momentum.xlsx skapad.")


if __name__=="__main__": main()
