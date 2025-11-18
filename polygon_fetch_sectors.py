import os, time
from pathlib import Path
import pandas as pd
import requests

API_KEY = os.environ.get("POLYGON_API_KEY", "").strip()
TICKER_FILE = "tickers.csv"               # din befintliga lista
OUTFILE = Path("public/data/sector_map.csv")

BASE_URL = "https://api.polygon.io/v3/reference/tickers"

def log(msg): 
    print(msg, flush=True)

def fetch_sector(ticker: str) -> dict:
    """Hämta sector/industry för en ticker från Polygon."""
    url = f"{BASE_URL}/{ticker}"
    r = requests.get(url, params={"apiKey": API_KEY}, timeout=8)
    r.raise_for_status()
    res = r.json().get("results", {}) or {}
    # Polygon har flera fält – vi plockar ut det som är mest användbart
    return {
        "Ticker": ticker,
        "Sector": res.get("sector") or "",
        "Industry": res.get("industry") or "",
        "Name": res.get("name") or ""
    }

def main():
    if not API_KEY:
        raise SystemExit("POLYGON_API_KEY saknas")

    if not Path(TICKER_FILE).exists():
        raise SystemExit(f"{TICKER_FILE} saknas")

    tickers = pd.read_csv(TICKER_FILE)["Ticker"].dropna().astype(str).unique()

    if OUTFILE.exists():
        df_map = pd.read_csv(OUTFILE)
    else:
        df_map = pd.DataFrame(columns=["Ticker","Sector","Industry","Name"])

    known = set(df_map["Ticker"])
    todo = [t for t in tickers if t not in known]

    log(f"[SECTOR] Har {len(known)} tickers i cache, {len(todo)} nya att hämta")

    rows = []
    for i, t in enumerate(todo, start=1):
        try:
            info = fetch_sector(t)
            rows.append(info)
            log(f"[SECTOR] {i}/{len(todo)} {t} → {info['Sector']} / {info['Industry']}")
            time.sleep(0.25)  # throttling
        except Exception as e:
            log(f"[WARN] sektorhämtning misslyckades för {t}: {e}")
            time.sleep(1.0)

    if rows:
        df_new = pd.DataFrame(rows)
        df_all = pd.concat([df_map, df_new], ignore_index=True)
    else:
        df_all = df_map

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(OUTFILE, index=False)
    log(f"[SECTOR] Sparat {len(df_all)} rader till {OUTFILE}")

if __name__ == "__main__":
    main()
