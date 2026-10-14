"""Run one fixed model using verified paired-gap and raw-liquidity evidence."""
import json
import os
from datetime import datetime, timezone
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
    # Individual endpoint evidence supersedes grouped rows, including missing days.
    for evidence_path in sorted(Path("universe_evidence").glob("histories_*.json")):
        for ticker, payloads in json.loads(evidence_path.read_text()).items():
            bases = {}
            for key, adjusted in (("raw", "false"), ("adjusted", "true")):
                payload = payloads[adjusted]
                if "error_type" in payload or not payload.get("results"):
                    raise RuntimeError(f"Unverified individual history for {ticker}: {key}")
                rows = {}
                for bar in payload["results"]:
                    day = datetime.fromtimestamp(bar["t"] / 1000, timezone.utc).date().isoformat()
                    rows[day] = {"open": bar["o"], "high": bar["h"], "low": bar["l"], "close": bar["c"], "volume": bar["v"]}
                bases[key] = rows
            verified_histories[ticker] = bases
    old_load_cache = engine.load_backtest_cache

    def corrected_cache(path, *args, **kwargs):
        cache, basis = old_load_cache(path, *args, **kwargs)
        for ticker, bases in verified_histories.items():
            for day_map in cache.values():
                day_map.pop(ticker, None)
            for day, row in bases["adjusted"].items():
                if day in cache:
                    cache[day][ticker] = row
        return cache, basis

    engine.load_backtest_cache = corrected_cache

    # Corporate-action consideration is in historical raw share units.
    # Each ticker's adjusted endpoint may include different subsequent splits.
    # Normalize to the original ticker's pre-action basis; never alter legal ratios.
    from audit_corporate_action_basis import adjustment_factor, convert_stock_row
    basis_client = engine.PolygonClient(os.environ["POLYGON_API_KEY"])
    paired_factors = {}

    def paired_factor(cache, ticker, day):
        key = (ticker, day)
        if key not in paired_factors:
            prices = []
            for adjusted in ("true", "false"):
                payload = basis_client._get(
                    f"/v2/aggs/ticker/{ticker}/range/1/day/{day}/{day}",
                    {"adjusted": adjusted, "sort": "asc", "limit": 10},
                )
                bars = payload.get("results", [])
                if len(bars) != 1:
                    raise RuntimeError(f"Missing paired action basis: {ticker} {day} {adjusted}")
                prices.append(float(bars[0]["c"]))
            cached = engine.get_from_map(cache.get(day, {}), ticker)
            if not cached or abs(float(cached["close"]) / prices[0] - 1.0) > 1e-6:
                raise RuntimeError(f"Action basis disagrees with execution cache: {ticker} {day}")
            paired_factors[key] = adjustment_factor(*prices)
        return paired_factors[key]

    from audit_dated_action_chain import install_dated_action_chain
    install_dated_action_chain(engine)
    from audit_action_price_install import install_compatible_action_prices
    install_compatible_action_prices(engine, paired_factor)

    # Execution-only distribution observations never replace formation histories.
    if os.environ["SCENARIO"] in ("momentum_selection_only", "eligible_universe_equal_weight"):
        from audit_multileg_action_install import install_compatible_multileg_actions
        multi_path = Path("audit_evidence/multileg_execution_histories_20261014.json")
        if multi_path.exists():
            install_compatible_multileg_actions(engine, paired_factor, json.loads(multi_path.read_text()))

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
        *args, execution_backfill=True, audit_equal_weight_all=os.environ["SCENARIO"] == "eligible_universe_equal_weight", **kwargs
    )
    flags = {"m12": True, "m6": True, "vol": True, "extension": True}
    specs = {
        "v4_baseline": (existing.v4_builder(flags), 10.0, False),
        "v4_stop_1_regime_0_extension_0": (existing.v4_builder({**flags, "extension": False}), 10.0, True),
        "simple_baseline": (existing.simple_builder, None, False),
        "simple_without_regime": (existing.simple_builder, None, True),
    }
    def universe_builder(tickers, latest, history, model, adv):
        candidates = existing.simple_builder(tickers, latest, history, model, adv)
        for candidate in candidates:
            candidate.total_score = 0.0
        return sorted(candidates, key=lambda candidate: candidate.ticker)

    specs["momentum_selection_only"] = (existing.simple_builder, None, True)
    specs["eligible_universe_equal_weight"] = (universe_builder, None, True)
    name = os.environ["SCENARIO"]
    if name not in specs:
        raise RuntimeError("Unknown fixed scenario: " + name)
    builder, stop, no_regime = specs[name]
    run = existing.run_one(name, builder, "2023-02-01", "2026-10-03", stop, no_regime)
    checks = controls.independent_check(run)
    # Keep the engine's selector unchanged; exported metadata names the actual audit scenario.
    run["positions"]["SelectionModel"] = name
    if "SelectionModel" in run["results"]:
        run["results"]["SelectionModel"] = name
    previous_path = SOURCE / f"{name}_positions.csv"
    previous = pd.read_csv(previous_path) if previous_path.exists() else None
    prior_keys = set(zip(previous.SignalDate, previous.Ticker)) if previous is not None else set()
    new_keys = set(zip(run["positions"].SignalDate, run["positions"].Ticker))
    run["positions"].to_csv(OUT / f"{name}_positions.csv", index=False)
    run["results"].to_csv(OUT / f"{name}_results.csv", index=False)
    record = {
        "scenario": name, "status": "COMPLETE", "metrics": run["metrics"],
        "out_of_sample_metrics": run["out_of_sample_metrics"], "checks": checks,
        "removed_position_keys": len(prior_keys - new_keys),
        "added_position_keys": len(new_keys - prior_keys),
        "spy_matched_monthly_fixed_cost_return_pct": float(((1.0 + (run["results"].SPYReturn_pct - engine.ROUND_TRIP_COST_PCT) / 100.0).prod() - 1.0) * 100.0),
    }
    (OUT / f"{name}_model_result.json").write_text(json.dumps(record, indent=2))
    print("VERIFIED_GAP_RESULT", json.dumps(record), flush=True)


if __name__ == "__main__":
    main()


