"""Freeze symbol-event evidence for unresolved valuations; no automatic inference."""
import json
import os
from pathlib import Path
from momentum_master_v3 import PolygonClient
def main():
    output = Path("Momentum_universe_symbol_events")
    output.mkdir(exist_ok=True)
    tickers = json.loads(Path("universe_unresolved_tickers.json").read_text())
    index = int(os.environ["CHUNK_INDEX"])
    client = PolygonClient(os.environ["POLYGON_API_KEY"])
    evidence = {}
    for ticker in tickers[index::8]:
        try:
            evidence[ticker] = client._get(f"/vX/reference/tickers/{ticker}/events", {})
        except Exception as exc:
            evidence[ticker] = {"error_type": type(exc).__name__}
        (output / f"events_{index}.json").write_text(json.dumps(evidence, allow_nan=False))
        print("EVENTS", ticker, flush=True)
if __name__ == "__main__":
    main()
