"""Fetch one deterministic chunk of paired raw/fresh-adjusted gap bars."""
import json
import os
from pathlib import Path

import backtest_momentum_v3 as engine
import run_corrected_component_audit as controls
import run_relaxed_selection_audit as selection
from momentum_master_v3 import PolygonClient
from run_verified_gap_correction_audit import OBSERVATION, grouped

OUT = Path("Momentum_gap_pair_chunk")


def main():
    OUT.mkdir(exist_ok=True)
    controls.SNAPSHOT.mkdir(exist_ok=True)
    controls.freeze_provider()
    cache, _basis = engine.load_backtest_cache(engine.CACHE_FILE)
    universes = engine.load_point_in_time_universe_cache(engine.UNIVERSE_CACHE_FILE)
    if not cache or not universes:
        raise RuntimeError("Missing validated frozen cache or point-in-time universes")
    relevant_rows = json.loads(
        Path("gap_evidence/otherwise_eligible_gap_excluded.json").read_text()
    )
    relevant_tickers = {row["Ticker"] for row in relevant_rows}
    days = sorted(cache)
    tickers = sorted({ticker for universe in universes.values() for ticker in universe})
    original = engine.find_unverified_split_basis_tickers(
        cache, days, tickers, selection.split_events()
    )
    original = {ticker: rows for ticker, rows in original.items() if ticker in relevant_tickers}
    if set(original) != relevant_tickers:
        raise RuntimeError("Relevant ticker set differs from original reconstruction")

    required_days = set()
    for ticker, observations in original.items():
        ticker_days = [day for day in days if engine.get_from_map(cache[day], ticker)]
        for text in observations:
            match = OBSERVATION.match(text)
            if not match:
                raise RuntimeError("Unparseable gap observation: " + text)
            day = match.group("day")
            earlier = [value for value in ticker_days if value < day]
            if not earlier:
                raise RuntimeError(f"No prior cached ticker row for {ticker} {day}")
            required_days.update((earlier[-1], day))

    chunk_index = int(os.environ["CHUNK_INDEX"])
    chunk_count = int(os.environ["CHUNK_COUNT"])
    selected_days = sorted(required_days)[chunk_index::chunk_count]
    client = PolygonClient(os.environ["POLYGON_API_KEY"])
    snapshots = {}
    for index, day in enumerate(selected_days, 1):
        raw = grouped(client, day, False)
        adjusted = grouped(client, day, True)
        snapshots[day] = {
            "raw": {ticker: raw[ticker] for ticker in relevant_tickers if ticker in raw},
            "adjusted": {
                ticker: adjusted[ticker]
                for ticker in relevant_tickers
                if ticker in adjusted
            },
        }
        print("GAP_PAIR_CHUNK_SESSION", index, len(selected_days), day, flush=True)
    (OUT / f"gap_pair_chunk_{chunk_index}.json").write_text(
        json.dumps(snapshots, separators=(",", ":"), allow_nan=False)
    )


if __name__ == "__main__":
    main()
