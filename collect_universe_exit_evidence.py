"""Collect individual histories for unresolved universe valuations; never impute."""
import json
import os
from pathlib import Path
from momentum_master_v3 import PolygonClient

def main():
    out = Path("Momentum_universe_exit_evidence")
    out.mkdir(exist_ok=True)
    tickers = json.loads(Path("universe_unresolved_tickers.json").read_text())
    index = int(os.environ["CHUNK_INDEX"])
    client = PolygonClient(os.environ["POLYGON_API_KEY"])
    records = {}
    for ticker in tickers[index::8]:
        records[ticker] = {}
        for basis in ("false", "true"):
            try:
                payload = client._get(
                    f"/v2/aggs/ticker/{ticker}/range/1/day/2021-01-01/2026-10-03",
                    {"adjusted": basis, "sort": "asc", "limit": 50000},
                )
                records[ticker][basis] = payload
            except Exception as exc:
                records[ticker][basis] = {"error_type": type(exc).__name__}
        (out / f"histories_{index}.json").write_text(json.dumps(records, allow_nan=False))
        print("COLLECTED", ticker, flush=True)

if __name__ == "__main__":
    main()
