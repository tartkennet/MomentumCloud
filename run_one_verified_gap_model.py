"""Run one fixed model using verified paired-gap and raw-liquidity evidence."""
import json
import os
from pathlib import Path

import pandas as pd

import backtest_momentum_v3 as engine
import run_corrected_component_audit as controls
import run_v4_ablation_and_simple_candidate as existing

OUT = Path("Momentum_verified_gap_model")
SOURCE = Path("raw_evidence")


def main():
    OUT.mkdir(exist_ok=True)
    manifest = json.loads(Path("classification/manifest.json").read_text())
    remaining = json.loads(Path("classification/remaining_data_quality_exclusions.json").read_text())
    verified_histories = json.loads(Path("classification/verified_ticker_histories.json").read_text())
    old_load_cache = engine.load_backtest_cache

    def corrected_cache(path):
        cache, basis = old_load_cache(path)
        for ticker, bases in verified_histories.items():
            for day, row in bases["adjusted"].items():
                if day in cache:
                    cache[day][ticker] = row
        return cache, basis

    engine.load_backtest_cache = corrected_cache
    old_raw_closes = engine.PolygonClient.fetch_unadjusted_signal_closes

    def corrected_raw_closes(client, day):
        values = old_raw_closes(client, day)
        for ticker, bases in verified_histories.items():
            row = bases["raw"].get(day)
            if row:
                values[ticker] = float(row["close"])
        return values

    engine.PolygonClient.fetch_unadjusted_signal_closes = corrected_raw_closes
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
            verified_raw = verified_histories.get(ticker, {}).get("raw", {}).get(day)
            if verified_raw:
                dollars.append(float(verified_raw["close"]) * float(verified_raw["volume"]))
            else:
                if ticker not in raw_volume.get(day, {}):
                    raise RuntimeError(f"Missing verified raw liquidity {day} {ticker}")
                dollars.append(raw_volume[day][ticker])
        if len(dollars) < 10:
            return None
        return value[0], sum(dollars) / len(dollars)

    existing.history_for = actual_history
    engine.find_unverified_split_basis_tickers = lambda *_args, **_kwargs: remaining
    original_run = engine.run
    engine.run = lambda *args, **kwargs: original_run(
        *args, execution_backfill=True, **kwargs
    )
    flags = {"m12": True, "m6": True, "vol": True, "extension": True}
    specs = {
        "v4_baseline": (existing.v4_builder(flags), 10.0, False),
        "v4_stop_1_regime_0_extension_0": (existing.v4_builder({**flags, "extension": False}), 10.0, True),
        "simple_baseline": (existing.simple_builder, None, False),
        "simple_without_regime": (existing.simple_builder, None, True),
    }
    name = os.environ["SCENARIO"]
    if name not in specs:
        raise RuntimeError("Unknown fixed scenario: " + name)
    builder, stop, no_regime = specs[name]
    run = existing.run_one(name, builder, "2023-02-01", "2026-10-03", stop, no_regime)
    checks = controls.independent_check(run)
    previous = pd.read_csv(SOURCE / f"{name}_positions.csv")
    prior_keys = set(zip(previous.SignalDate, previous.Ticker))
    new_keys = set(zip(run["positions"].SignalDate, run["positions"].Ticker))
    run["positions"].to_csv(OUT / f"{name}_positions.csv", index=False)
    run["results"].to_csv(OUT / f"{name}_results.csv", index=False)
    record = {
        "scenario": name, "status": "COMPLETE", "metrics": run["metrics"],
        "out_of_sample_metrics": run["out_of_sample_metrics"], "checks": checks,
        "removed_position_keys": len(prior_keys - new_keys),
        "added_position_keys": len(new_keys - prior_keys),
    }
    (OUT / f"{name}_model_result.json").write_text(json.dumps(record, indent=2))
    print("VERIFIED_GAP_RESULT", json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
