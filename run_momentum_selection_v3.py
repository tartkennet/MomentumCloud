"""Compare two freer selectors while freezing the complete v2 risk policy."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import traceback

import numpy as np
import pandas as pd

import momentum_selection_v3 as selection
import risk_managed_momentum as risk
import run_risk_managed_research as execution
from selection_v3_execution import install_action, documented_unfilled_entry, install_disclosed_stale_marks

OUT = Path("audit_evidence/selection_v3_20261020")
BASE = Path("audit_evidence/robust_locked_20261019")
OLD = Path("audit_evidence/risk_managed_v2_20261020")
VARIANTS = ("strict_v2", *selection.SELECTORS)


def load_raw_dollars(replay):
    values = json.loads(Path("raw_evidence/raw_dollar_volume.json").read_text())
    full = json.loads(Path("classification/verified_ticker_histories.json").read_text())
    for ticker, bases in full.items():
        for day, row in bases["raw"].items():
            values.setdefault(day, {})[ticker] = float(row["close"]) * float(row["volume"])
    for ticker, bases in replay.histories.items():
        for row in bases["false"].get("results", []):
            day = datetime.fromtimestamp(row["t"] / 1000, timezone.utc).date().isoformat()
            values.setdefault(day, {})[ticker] = float(row["c"]) * float(row["v"])
    return values


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    execution.OUT = OUT  # Only this process's NEW artifacts use the shared writer.
    save = lambda name, obj: execution.save_json(OUT / name, obj)
    original_files = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in OLD.glob("*") if path.is_file()}
    record = {"status": "STARTED", "approval": "RESEARCH_ONLY_UNVALIDATED",
              "selection_configuration": asdict(selection.CONFIG),
              "risk_configuration_unchanged": risk.CONFIG.to_dict(),
              "variants_predeclared": VARIANTS,
              "spec_sha256_before_returns": hashlib.sha256(Path("docs/momentum_selection_v3_spec.md").read_bytes()).hexdigest(),
              "holdout": "Previously examined data; not fresh out-of-sample or a production recommendation."}
    try:
        import replay_verified_audit_offline as replay
        record["input_install"] = replay.audit.install_verified_inputs("robust_locked_candidate")
        engine = replay.engine
        install_action(engine)
        cache, basis = engine.load_backtest_cache(None)
        days = sorted(cache)
        context = {}
        stale_uses = install_disclosed_stale_marks(engine, cache, days, [
            OUT / "execution_original_responses.json", OUT / "last_window_original_responses.json"], context)
        record["price_basis"] = basis
        periods = pd.read_csv(BASE / "Momentum_backtest_results.csv")
        raw_dollars = load_raw_dollars(replay)
        client = engine.PolygonClient("OFFLINE_NO_NETWORK")
        splits = {}
        for row in client.fetch_recent_splits("2021-11-08", "2026-10-03"):
            splits.setdefault(row["ticker"], []).append(row)
        lots, signals, missing = {name: [] for name in VARIANTS}, [], {}
        unfilled = []
        benchmarks = {"spy_buy_hold": [], **{"spy_matched_" + name: [] for name in VARIANTS}}
        for period in periods.itertuples():
            signal = period.SignalDate
            history = [(day, cache[day]) for day in days if day <= signal][-253:][::-1]
            universe = engine.fetch_point_in_time_universe(client, signal, locked_robust=True)
            raw_closes = client.fetch_unadjusted_signal_closes(signal)
            strict, strict_exclusions = risk.rank_candidates(universe, history, signal, raw_closes, raw_dollars)
            rankings, broad_exclusions = selection.rank_candidates(universe, history, signal, raw_closes, raw_dollars)
            rankings["strict_v2"] = strict
            risk_on = risk.spy_risk_on(history)
            if risk_on != (period.RiskRegime != "CASH"):
                raise AssertionError("Monthly market gate changed")
            regime_signal = regime_exit = None
            for day in days:
                if not period.EntryDate <= day < period.ExitDate:
                    continue
                close_history = [(d, cache[d]) for d in days if d <= day][-200:][::-1]
                if not risk.spy_risk_on(close_history):
                    regime_signal, regime_exit = day, days[days.index(day) + 1]
                    break
            signal_record = {"signal": signal, "universe_count": len(universe),
                             "strict_exclusions": strict_exclusions, "broad_exclusions": broad_exclusions,
                             "risk_on": risk_on, "market_exit_signal": regime_signal,
                             "market_exit": regime_exit, "variants": {}}
            exposures = {}
            strict_names = {c.ticker for c in strict}
            for name in VARIANTS:
                context.update(variant=name, stage="STOP_MONITORING")
                chosen = rankings[name][:risk.CONFIG.position_count] if risk_on else []
                weights, sizing = risk.allocation(chosen, history, signal)
                exposures[name] = sum(weights.values())
                signal_record["variants"][name] = {
                    "qualified_count": len(rankings[name]), "selected": [asdict(c) for c in chosen],
                    "weights": weights, "sizing": sizing,
                    "selected_not_eligible_in_strict_v2": [c.ticker for c in chosen if c.ticker not in strict_names]}
                for candidate in chosen:
                    try:
                        canceled = documented_unfilled_entry(engine, cache, candidate.ticker, period.EntryDate)
                        if canceled:
                            unfilled.append({**canceled, "variant": name, "signal": signal,
                                             "intended_weight": weights[candidate.ticker]})
                            exposures[name] -= weights[candidate.ticker]
                            continue
                        lots[name].append(execution.execute_lot(engine, cache, days, splits, candidate,
                                                               period, weights[candidate.ticker], regime_exit))
                    except RuntimeError as error:
                        key = str(error)
                        detail = {"error": key, "variant": name, "ticker": candidate.ticker, "signal": signal}
                        if key.startswith("OFFLINE_REQUEST_MISSING "):
                            detail["request"] = json.loads(key.split(" ", 1)[1])
                        missing[(name, signal, candidate.ticker)] = detail
                        save("missing_evidence.json", list(missing.values()))
            spy_entry = execution.actual_price(engine, cache, days, splits, "SPY", period.EntryDate)
            cases = [("spy_buy_hold", 1.0, period.ExitDate)]
            cases += [("spy_matched_" + name, exposures[name], regime_exit or period.ExitDate) for name in VARIANTS]
            for name, exposure, exit_day in cases:
                if exposure <= 0:
                    continue
                price = execution.actual_price(engine, cache, days, splits, "SPY", exit_day)
                benchmarks[name].append({"SignalDate": signal, "Ticker": "SPY", "Weight": exposure,
                    "EntryDate": period.EntryDate, "PlannedExitDate": period.ExitDate, "ExitDate": exit_day,
                    "EntryPrice_USD": spy_entry, "ExitPrice_USD": price, "ExitReason": "BENCHMARK",
                    "GrossReturn_pct": (price / spy_entry - 1) * 100})
            signals.append(signal_record)
            save("signals.json", signals)
            save("unfilled_orders.json", unfilled)
            print("COMPLETE_SIGNAL", signal, "strict", len(strict), "broad", len(rankings[selection.SELECTORS[0]]),
                  "evidence_gaps", len(missing), flush=True)
        blocked = {name: [row for row in missing.values() if row["variant"] == name]
                   for name in VARIANTS if any(row["variant"] == name for row in missing.values())}
        record["blocked_variants"] = blocked
        if "strict_v2" in blocked or "broad_momentum" in blocked:
            raise RuntimeError("Primary selection or baseline evidence gaps: no complete primary comparison accepted")
        record["models"] = {}
        for name, trades in lots.items():
            if name not in blocked:
                context.update(variant=name, stage="NAV")
                record["models"][name] = execution.aggregate(engine, cache, days, periods, trades, name)
        record["benchmarks"] = {name: execution.aggregate(engine, cache, days, periods, trades, name)
                                 for name, trades in benchmarks.items()
                                 if not any(name == "spy_matched_" + variant for variant in blocked)}
        archived = json.loads((OLD / "comparison.json").read_text())["models"]["full_v2"]
        for key in ("net_return_pct", "gross_return_pct", "daily_drawdown_pct", "positions", "stop_exits", "market_exits"):
            if not np.isclose(record["models"]["strict_v2"][key], archived[key], atol=1e-8, rtol=0):
                raise AssertionError("Strict v2 parity failed: " + key)
        actual = pd.read_csv(OUT / "strict_v2_results.csv")
        archived_monthly = pd.read_csv(OLD / "full_v2_results.csv")
        pd.testing.assert_frame_equal(actual, archived_monthly, check_exact=False, rtol=0, atol=1e-9)
        record["strict_v2_parity"] = "PASS_EXACT_POLICY_AND_MONTHLY_RESULTS"
        record["breadth"] = {name: {
            "mean_eligible": float(np.mean([s["variants"][name]["qualified_count"] for s in signals])),
            "minimum_eligible": min(s["variants"][name]["qualified_count"] for s in signals),
            "maximum_eligible": max(s["variants"][name]["qualified_count"] for s in signals),
            "chosen_lots_ineligible_under_strict_v2": sum(len(s["variants"][name]["selected_not_eligible_in_strict_v2"]) for s in signals)}
            for name in VARIANTS}
        record["status"] = ("COMPLETE_PRIMARY_SELECTION_COMPARISON_SECONDARY_BLOCKED" if blocked
                            else "COMPLETE_FIXED_RISK_SELECTION_COMPARISON")
        record["unfilled_orders"] = unfilled
        record["stale_marks"] = list(stale_uses.values())
        record["observed_only_validation"] = not bool(stale_uses)
        save("stale_mark_uses.json", list(stale_uses.values()))
        record["limitations"] = [
            "All periods already examined; this exploratory comparison does not establish unseen outperformance.",
            "Only price return and fractional weights, fixed monthly cost and zero cash interest are modeled.",
            "Raw price/liquidity gates are looser as well as the removed trend/volatility/extension gates.",
            "Different selected stocks naturally produce different realized weights and stop dates under the same risk policy.",
            "Individual market-price and dated-issuer evidence is not complete for all newly selected lots.",
            "Disclosed last-reported marks on paired-source-confirmed missing closes estimate NAV; fresh closes and missed stop signals cannot be verified there.",
            "Initial exposure matched SPY does not duplicate every stock's subsequent stop path.",
        ]
        for filename in (("traceback.txt",) if blocked else ("missing_evidence.json", "traceback.txt")):
            (OUT / filename).unlink(missing_ok=True)
    except Exception as error:
        record.update(status="BLOCKED_NO_COMPLETE_SELECTION_COMPARISON", error=str(error))
        (OUT / "traceback.txt").write_text(traceback.format_exc())
        raise
    finally:
        for name, digest in original_files.items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
                raise AssertionError("Archived v2 evidence was changed: " + name)
        record["source_sha256"] = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (
            "momentum_selection_v3.py", "run_momentum_selection_v3.py", "risk_managed_momentum.py",
            "run_risk_managed_research.py", "selection_v3_execution.py", "docs/momentum_selection_v3_spec.md")}
        save("comparison.json", record)
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
