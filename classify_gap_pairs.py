"""Classify reconstructed gap observations from merged paired-bar chunks."""
import json
from pathlib import Path

import pandas as pd

import backtest_momentum_v3 as engine
import run_relaxed_selection_audit as selection
from run_verified_gap_correction_audit import OBSERVATION, relative_match

OUT = Path("Momentum_verified_gap_classification")


def main():
    OUT.mkdir(exist_ok=True)
    cache, basis = engine.load_backtest_cache(engine.CACHE_FILE)
    universes = engine.load_point_in_time_universe_cache(engine.UNIVERSE_CACHE_FILE)
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

    histories = {}
    for path in sorted(Path("gap_chunks").glob("gap_ticker_history_*.json")):
        chunk = json.loads(path.read_text())
        overlap = set(histories) & set(chunk)
        if overlap:
            raise RuntimeError("Duplicate chunk tickers: " + ",".join(sorted(overlap)))
        histories.update(chunk)
    if set(histories) != relevant_tickers:
        raise RuntimeError("Ticker-history chunks do not exactly cover relevant tickers")

    parsed = []
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
            parsed.append(
                {
                    "Ticker": ticker,
                    "Day": day,
                    "PriorDay": earlier[-1],
                    "CacheFactor": float(match.group("open")) / float(match.group("prior")),
                    "HeuristicRatio": float(match.group("ratio")),
                    "Observation": text,
                }
            )

    buckets = {key: [] for key in ("real", "transform", "stale", "unresolved")}
    for item in parsed:
        ticker, day, prior_day = item["Ticker"], item["Day"], item["PriorDay"]
        ticker_history = histories.get(ticker, {})
        raw_before = ticker_history.get("raw", {}).get(prior_day)
        raw_after = ticker_history.get("raw", {}).get(day)
        adjusted_before = ticker_history.get("adjusted", {}).get(prior_day)
        adjusted_after = ticker_history.get("adjusted", {}).get(day)
        if not all((raw_before, raw_after, adjusted_before, adjusted_after)):
            item["Classification"] = "UNRESOLVED_MISSING_PAIRED_BAR"
            buckets["unresolved"].append(item)
            continue
        values = [
            raw_before.get("close"), raw_after.get("open"),
            adjusted_before.get("close"), adjusted_after.get("open"),
        ]
        if any(value is None or float(value) <= 0 for value in values):
            item["Classification"] = "UNRESOLVED_INVALID_PAIRED_BAR"
            buckets["unresolved"].append(item)
            continue
        raw_factor = float(raw_after["open"]) / float(raw_before["close"])
        adjusted_factor = float(adjusted_after["open"]) / float(adjusted_before["close"])
        item.update({
            "RawPriorClose": float(raw_before["close"]), "RawOpen": float(raw_after["open"]),
            "RawFactor": raw_factor,
            "FreshAdjustedPriorClose": float(adjusted_before["close"]),
            "FreshAdjustedOpen": float(adjusted_after["open"]),
            "FreshAdjustedFactor": adjusted_factor,
        })
        cache_matches = relative_match(item["CacheFactor"], adjusted_factor)
        raw_matches = relative_match(raw_factor, adjusted_factor)
        adjusted_continuous = relative_match(adjusted_factor, 1.0, 0.15)
        if cache_matches and raw_matches:
            item["Classification"] = "VERIFIED_REAL_MARKET_GAP"
            buckets["real"].append(item)
        elif cache_matches and adjusted_continuous and not raw_matches:
            item["Classification"] = "VERIFIED_CORPORATE_ACTION_TRANSFORM"
            buckets["transform"].append(item)
        elif not cache_matches:
            item["Classification"] = "STALE_OR_INCONSISTENT_ADJUSTED_CACHE"
            buckets["stale"].append(item)
        else:
            item["Classification"] = "UNRESOLVED_FACTOR_DISAGREEMENT"
            buckets["unresolved"].append(item)

    evidence = buckets["real"] + buckets["transform"] + buckets["stale"] + buckets["unresolved"]
    pd.DataFrame(evidence).to_csv(OUT / "paired_gap_verification.csv", index=False)
    (OUT / "paired_gap_verification.json").write_text(json.dumps(evidence, indent=2, allow_nan=False))
    remaining = {}
    for item in buckets["unresolved"]:
        remaining.setdefault(item["Ticker"], []).append(item["Observation"])
    (OUT / "remaining_data_quality_exclusions.json").write_text(json.dumps(remaining, indent=2))
    repaired_tickers = sorted({item["Ticker"] for item in buckets["stale"]})
    (OUT / "verified_ticker_histories.json").write_text(
        json.dumps(histories, separators=(",", ":"), allow_nan=False)
    )
    status = "COMPLETE_WITH_VERIFIED_HISTORY_REPAIRS" if repaired_tickers else "COMPLETE"
    manifest = {
        "status": status,
        "observations": len(parsed), "unique_tickers": len(original),
        "otherwise_eligible_candidate_months": len(relevant_rows),
        "verified_real_market_gaps": len(buckets["real"]),
        "verified_corporate_action_transforms": len(buckets["transform"]),
        "confirmed_data_errors": len(buckets["stale"]),
        "unresolved_fail_closed": len(buckets["unresolved"]),
        "repaired_tickers": repaired_tickers,
        "remaining_excluded_tickers": len(remaining), "price_basis_date": basis,
        "no_parameter_search": True, "selection_used_future_outcomes": False,
        "next_action": "run fixed models with full per-ticker history overrides",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("GAP_CLASSIFICATION", json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
