"""Freeze historical issuer identity; no automatic settlement or price inference."""
import json
import os
from datetime import date as Date, timedelta
from pathlib import Path
from momentum_master_v3 import PolygonClient

def request(client, path, params):
    try:
        return client._get(path, params)
    except Exception as exc:
        response = getattr(exc, "response", None)
        return {"error_type": type(exc).__name__,
                "http_status": getattr(response, "status_code", None)}

def main():
    output = Path("Momentum_universe_symbol_events")
    output.mkdir(exist_ok=True)
    pairs = json.loads(Path("universe_identity_requests.json").read_text())
    index = int(os.environ["CHUNK_INDEX"])
    client = PolygonClient(os.environ["POLYGON_API_KEY"])
    evidence = {}
    for pair in pairs[index::8]:
        ticker, date = pair["ticker"], pair["date"]
        details = request(client, f"/v3/reference/tickers/{ticker}", {"date": date})
        figi = details.get("results", {}).get("composite_figi")
        item = {"ticker": ticker, "as_of": date, "details": details}
        if figi:
            item["events_by_historical_figi"] = request(
                client, f"/vX/reference/tickers/{figi}/events", {})
        else:
            item["events_status"] = "NO_HISTORICAL_FIGI_NO_INFERENCE"
        cik = details.get("results", {}).get("cik")
        if cik:
            item["primary_filings"] = request(client, "/stocks/filings/8-K/vX/text", {
                "cik": str(cik).zfill(10),
                "filing_date.gte": date,
                "filing_date.lte": (Date.fromisoformat(date) + timedelta(days=70)).isoformat(),
                "limit": 100, "sort": "filing_date.asc"})
        evidence[f"{ticker}|{date}"] = item
        (output / f"identities_{index}.json").write_text(json.dumps(evidence, allow_nan=False))
        print("IDENTITY", ticker, date, flush=True)

if __name__ == "__main__":
    main()
