"""Verify every split-like gap from raw and freshly adjusted bars; rerun fixed audits."""
import json
import math
import os
import re
import shutil
from pathlib import Path

import pandas as pd

import backtest_momentum_v3 as engine
import run_corrected_component_audit as controls
import run_raw_liquidity_selection_audit as raw_audit
import run_relaxed_selection_audit as selection
import run_v4_ablation_and_simple_candidate as existing
from momentum_master_v3 import PolygonClient

OUT = Path("Momentum_verified_gap_audit")
SOURCE = Path("raw_evidence")
OBSERVATION = re.compile(
    r"^(?P<day>\d{4}-\d{2}-\d{2}): open (?P<open>[0-9.]+) "
    r"vs prior close (?P<prior>[0-9.]+), split-like ratio (?P<ratio>[0-9.]+)$"
)


def grouped(client, day, adjusted):
    payload = client._get(
        "/v2/aggs/grouped/locale/us/market/stocks/" + day,
        {"adjusted": "true" if adjusted else "false"},
    )
    rows = {
        str(row.get("T", "")).upper(): row
        for row in payload.get("results", []) or []
        if row.get("T")
    }
    if len(rows) < 1000:
        raise RuntimeError(f"Incomplete grouped response {day} adjusted={adjusted}")
    return rows


def relative_match(left, right, tolerance=0.02):
    return (
        left > 0
        and right > 0
        and abs(math.log(left / right)) <= math.log(1.0 + tolerance)
    )


def main():
    OUT.mkdir(exist_ok=True)
    controls.SNAPSHOT.mkdir(exist_ok=True)
    controls.freeze_provider()
    cache, basis = engine.load_backtest_cache(engine.CACHE_FILE)
    universes = engine.load_point_in_time_universe_cache(engine.UNIVERSE_CACHE_FILE)
    if not cache or not universes:
        raise RuntimeError("Missing validated frozen cache or point-in-time universes")
    days = sorted(cache)
    tickers = sorted({ticker for universe in universes.values() for ticker in universe})
    original = engine.find_unverified_split_basis_tickers(
        cache, days, tickers, selection.split_events()
    )
    parsed = []
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
            prior_day = earlier[-1]
            parsed.append(
                {
                    "Ticker": ticker,
                    "Day": day,
                    "PriorDay": prior_day,
                    "CacheFactor": float(match.group("open")) / float(match.group("prior")),
                    "HeuristicRatio": float(match.group("ratio")),
                    "Observation": text,
                }
            )
            required_days.update((prior_day, day))
    client = PolygonClient(os.environ["POLYGON_API_KEY"])
    snapshots = {}
    for index, day in enumerate(sorted(required_days), 1):
        snapshots[(day, False)] = grouped(client, day, False)
        snapshots[(day, True)] = grouped(client, day, True)
        print("GAP_PAIR_SESSION", index, len(required_days), day, flush=True)
    verified_real, verified_transform, data_errors, unresolved = [], [], [], []
    for item in parsed:
        ticker, day, prior_day = item["Ticker"], item["Day"], item["PriorDay"]
        raw_before = snapshots[(prior_day, False)].get(ticker)
        raw_after = snapshots[(day, False)].get(ticker)
        adjusted_before = snapshots[(prior_day, True)].get(ticker)
        adjusted_after = snapshots[(day, True)].get(ticker)
        if not all((raw_before, raw_after, adjusted_before, adjusted_after)):
            item.update({"Classification": "UNRESOLVED_MISSING_PAIRED_BAR"})
            unresolved.append(item)
            continue
        values = [
            raw_before.get("c"),
            raw_after.get("o"),
            adjusted_before.get("c"),
            adjusted_after.get("o"),
        ]
        if any(value is None or float(value) <= 0 for value in values):
            item.update({"Classification": "UNRESOLVED_INVALID_PAIRED_BAR"})
            unresolved.append(item)
            continue
        raw_factor = float(raw_after["o"]) / float(raw_before["c"])
        adjusted_factor = float(adjusted_after["o"]) / float(adjusted_before["c"])
        item.update(
            {
                "RawPriorClose": float(raw_before["c"]),
                "RawOpen": float(raw_after["o"]),
                "RawFactor": raw_factor,
                "FreshAdjustedPriorClose": float(adjusted_before["c"]),
                "FreshAdjustedOpen": float(adjusted_after["o"]),
                "FreshAdjustedFactor": adjusted_factor,
            }
        )
        cache_matches_fresh = relative_match(item["CacheFactor"], adjusted_factor)
        raw_matches_adjusted = relative_match(raw_factor, adjusted_factor)
        adjusted_is_continuous = relative_match(adjusted_factor, 1.0, 0.15)
        if cache_matches_fresh and raw_matches_adjusted:
            item["Classification"] = "VERIFIED_REAL_MARKET_GAP"
            verified_real.append(item)
        elif cache_matches_fresh and adjusted_is_continuous and not raw_matches_adjusted:
            item["Classification"] = "VERIFIED_CORPORATE_ACTION_TRANSFORM"
            verified_transform.append(item)
        elif not cache_matches_fresh:
            item["Classification"] = "STALE_OR_INCONSISTENT_ADJUSTED_CACHE"
            data_errors.append(item)
        else:
            item["Classification"] = "UNRESOLVED_FACTOR_DISAGREEMENT"
            unresolved.append(item)
    evidence = verified_real + verified_transform + data_errors + unresolved
    pd.DataFrame(evidence).to_csv(OUT / "paired_gap_verification.csv", index=False)
    (OUT / "paired_gap_verification.json").write_text(
        json.dumps(evidence, indent=2, allow_nan=False)
    )
    remaining = {}
    for item in data_errors + unresolved:
        remaining.setdefault(item["Ticker"], []).append(item["Observation"])
    (OUT / "remaining_data_quality_exclusions.json").write_text(
        json.dumps(remaining, indent=2)
    )
    if data_errors:
        (OUT / "manifest.json").write_text(
            json.dumps(
                {
                    "status": "BLOCKED_BY_CONFIRMED_STALE_ADJUSTED_DATA",
                    "observations": len(parsed),
                    "verified_real_market_gaps": len(verified_real),
                    "verified_corporate_action_transforms": len(verified_transform),
                    "confirmed_data_errors": len(data_errors),
                    "unresolved": len(unresolved),
                    "next_action": "repair adjusted history before rerunning models",
                },
                indent=2,
            )
        )
        raise RuntimeError("Confirmed stale adjusted data requires explicit history repair")
    if unresolved:
        print("UNRESOLVED_GAPS_REMAIN_FAIL_CLOSED", len(unresolved), flush=True)

    # Keep actual raw historical dollar volume and fail closed if unavailable.
    raw_volume = json.loads((SOURCE / "raw_dollar_volume.json").read_text())
    old_history = existing.history_for

    def actual_history(ticker, latest, history):
        value = old_history(ticker, latest, history)
        if value is None:
            return None
        dollars = []
        for day, grouped_map in history[:20]:
            row = engine.get_from_map(grouped_map, ticker)
            if row is None or row.get("volume") is None:
                continue
            if ticker not in raw_volume.get(day, {}):
                raise RuntimeError(f"Missing verified raw liquidity {day} {ticker}")
            dollars.append(raw_volume[day][ticker])
        if len(dollars) < 10:
            return None
        return value[0], sum(dollars) / len(dollars)

    existing.history_for = actual_history
    engine.find_unverified_split_basis_tickers = lambda *_args, **_kwargs: remaining
    flags = {"m12": True, "m6": True, "vol": True, "extension": True}
    specs = [
        ("v4_baseline", existing.v4_builder(flags), 10.0, False),
        (
            "v4_stop_1_regime_0_extension_0",
            existing.v4_builder({**flags, "extension": False}),
            10.0,
            True,
        ),
        ("simple_baseline", existing.simple_builder, None, False),
        ("simple_without_regime", existing.simple_builder, None, True),
    ]
    records = []
    for name, builder, stop, no_regime in specs:
        run = existing.run_one(
            name, builder, "2023-02-01", "2026-10-03", stop, no_regime
        )
        checks = controls.independent_check(run)
        previous = pd.read_csv(SOURCE / f"{name}_positions.csv")
        prior_keys = set(zip(previous.SignalDate, previous.Ticker))
        new_keys = set(zip(run["positions"].SignalDate, run["positions"].Ticker))
        run["positions"].to_csv(OUT / f"{name}_positions.csv", index=False)
        run["results"].to_csv(OUT / f"{name}_results.csv", index=False)
        record = {
            "scenario": name,
            "status": "COMPLETE",
            "metrics": run["metrics"],
            "out_of_sample_metrics": run["out_of_sample_metrics"],
            "checks": checks,
            "removed_position_keys": len(prior_keys - new_keys),
            "added_position_keys": len(new_keys - prior_keys),
        }
        records.append(record)
        print("VERIFIED_GAP_RESULT", json.dumps(record), flush=True)
    (OUT / "model_results.json").write_text(json.dumps(records, indent=2))
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "status": "COMPLETE",
                "observations": len(parsed),
                "unique_tickers": len(original),
                "verified_real_market_gaps": len(verified_real),
                "verified_corporate_action_transforms": len(verified_transform),
                "confirmed_data_errors": len(data_errors),
                "unresolved_fail_closed": len(unresolved),
                "remaining_excluded_tickers": len(remaining),
                "price_basis_date": basis,
                "no_parameter_search": True,
                "selection_used_future_outcomes": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
