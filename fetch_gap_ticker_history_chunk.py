"""Fetch full per-ticker raw and adjusted histories for one deterministic chunk."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import run_corrected_component_audit as controls
from momentum_master_v3 import PolygonClient

OUT = Path("Momentum_gap_ticker_history_chunk")


def history(client, ticker, adjusted):
    payload = client._get(
        f"/v2/aggs/ticker/{ticker}/range/1/day/2021-01-01/2026-10-03",
        {"adjusted": "true" if adjusted else "false", "sort": "asc", "limit": 50000},
    )
    rows = {}
    for row in payload.get("results", []) or []:
        timestamp = row.get("t")
        if timestamp is None or row.get("c") is None:
            continue
        day = datetime.fromtimestamp(float(timestamp) / 1000, timezone.utc).date().isoformat()
        close = float(row["c"])
        rows[day] = {
            "open": float(row.get("o", close)), "high": float(row.get("h", close)),
            "low": float(row.get("l", close)), "close": close,
            "volume": float(row.get("v", 0.0) or 0.0),
        }
    if len(rows) < 250:
        raise RuntimeError(f"Incomplete individual history for {ticker}: {len(rows)} rows")
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    controls.SNAPSHOT.mkdir(exist_ok=True)
    controls.freeze_provider()
    evidence = json.loads(Path("gap_evidence/otherwise_eligible_gap_excluded.json").read_text())
    tickers = sorted({row["Ticker"] for row in evidence})
    index, count = int(os.environ["CHUNK_INDEX"]), int(os.environ["CHUNK_COUNT"])
    selected = tickers[index::count]
    client = PolygonClient(os.environ["POLYGON_API_KEY"])
    output = {}
    for number, ticker in enumerate(selected, 1):
        output[ticker] = {
            "raw": history(client, ticker, False),
            "adjusted": history(client, ticker, True),
        }
        print("TICKER_HISTORY", number, len(selected), ticker, flush=True)
    (OUT / f"gap_ticker_history_{index}.json").write_text(
        json.dumps(output, separators=(",", ":"), allow_nan=False)
    )


if __name__ == "__main__":
    main()
