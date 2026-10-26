#!/usr/bin/env python3
"""Replay the frozen Core candidate; exports paper intentions, never broker orders."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import logging
import os
import re
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from momentum_core import CONFIG, MODEL, DataBlocked, Ledger, gates, metrics
from momentum_core_data import CoreData, atomic_json
from momentum_master_v3 import PolygonClient


ROOT = Path(__file__).resolve().parent
SOURCE_FILES = ("momentum_core.py", "momentum_core_data.py", "run_momentum_core.py",
                "momentum_master_v3.py", "backtest_momentum_v3.py", "momentum_strategy.py",
                "momentum_config.py", "requirements.txt", "docs/MOMENTUM_CORE_PROTOCOL.md")
FORWARD_START = "2026-10-27"
FIRST_PAPER_DEADLINE = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def source_fingerprint():
    digest = hashlib.sha256()
    for name in SOURCE_FILES:
        digest.update(name.encode() + b"\0" + hashlib.sha256((ROOT / name).read_bytes()).digest())
    return digest.hexdigest()


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def replay(data, config=CONFIG):
    strategy, benchmark = Ledger(cash=config.initial_cash), Ledger(cash=config.initial_cash)
    strategy.first_is_month_boundary = data.first_is_month_boundary()
    for day in data.sessions:
        benchmark.step(data, day, config, benchmark=True)
        strategy.step(data, day, config)
    result, periods = metrics(strategy, benchmark)
    return strategy, benchmark, result, periods


def verify_forward_prefix(strategy, previous, end):
    if previous:
        cutoff = previous["last_date"]
        if end < cutoff:
            raise DataBlocked("Forward record cannot move backwards")
        for field, date_key in (("equity", "date"), ("trades", "date"), ("targets", "date")):
            actual = [row for row in getattr(strategy, field) if row[date_key] <= cutoff]
            if actual != previous[field]:
                raise DataBlocked(f"Forward {field} changed before {cutoff}; historical revision blocked")


def resume_paper(data, checkpoint, config=CONFIG, *, stress=False):
    prefix = "stress_" if stress else ""
    old_strategy, old_benchmark = checkpoint[prefix + "strategy"], checkpoint[prefix + "benchmark"]
    strategy = Ledger(**copy.deepcopy(old_strategy))
    benchmark = Ledger(**copy.deepcopy(old_benchmark))
    if strategy.last_date != benchmark.last_date:
        raise DataBlocked("Strategy and benchmark checkpoint dates differ")
    for day in data.sessions:
        benchmark.step(data, day, config, benchmark=True)
        strategy.step(data, day, config)
    cutoff = data.sessions[-1] if data.sessions else strategy.last_date
    verify_forward_prefix(strategy, old_strategy, cutoff)
    verify_forward_prefix(benchmark, old_benchmark, cutoff)
    result, periods = metrics(strategy, benchmark)
    return strategy, benchmark, result, periods


def base_decision(start, end, mode):
    return {"model": MODEL, "source_fingerprint": source_fingerprint(),
            "source_commit": os.getenv("GITHUB_SHA"), "start": start, "end": end,
            "created_at": datetime.now(timezone.utc).isoformat(), "config": asdict(CONFIG),
            "evidence_class": "FORWARD_PAPER" if mode == "paper" else "DEVELOPMENT",
            "live_approved": False, "broker_orders_enabled": False,
            "historical_pass_is_live_approval": False}


def run(start, end, output_dir, cache_dir, mode="development"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    decision = base_decision(start, end, mode)
    decision_path = output / "Momentum_core_decision.json"
    state_path = output / "Momentum_core_state.json"
    checkpoint_path = output / "Momentum_core_paper_checkpoint.json"
    checkpoint = None
    # Invalidate stale success before touching any market input.
    decision.update(status="RUNNING", metrics={}, gates=[])
    atomic_json(decision_path, decision)
    atomic_json(output / "Momentum_core_paper_orders.json", {
        "status": "RUNNING", "live_approved": False, "broker_orders_enabled": False,
        "intentions_for_next_observed_session": None})
    for name in ("daily", "trades", "periods"):
        write_csv(output / f"Momentum_core_{name}.csv", [])
    try:
        if mode == "paper" and checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if checkpoint.get("source_fingerprint") != decision["source_fingerprint"]:
                raise DataBlocked("Forward checkpoint source changed; preserve prior record")
        if mode == "paper" and start != FORWARD_START:
            raise ValueError(f"Forward paper start is frozen at {FORWARD_START}")
        if mode == "paper" and end < start:
            decision["status"] = "PAPER_WAITING_FOR_SESSIONS"
            atomic_json(output / "Momentum_core_paper_orders.json", {
                "status": decision["status"], "live_approved": False,
                "broker_orders_enabled": False, "intentions_for_next_observed_session": None})
            atomic_json(decision_path, decision)
            return decision
        if end >= date.today().isoformat():
            raise ValueError("End date must precede the current UTC date: only completed EOD inputs")
        key = os.getenv("POLYGON_API_KEY")
        if not key:
            raise DataBlocked("POLYGON_API_KEY is missing")
        # Forbid silently replacing an existing forward record after changing code.
        identity_path = output / "Momentum_core_paper_identity.json"
        if mode == "paper":
            if identity_path.exists():
                identity = json.loads(identity_path.read_text(encoding="utf-8"))
                if identity.get("source_fingerprint") != decision["source_fingerprint"]:
                    raise DataBlocked("Forward paper source changed; preserve prior record and freeze a new version")
            else:
                atomic_json(identity_path, {"model": MODEL, "start": start,
                                           "source_fingerprint": decision["source_fingerprint"]})
            if checkpoint is None and datetime.now(timezone.utc) > FIRST_PAPER_DEADLINE:
                raise DataBlocked("Missing original forward checkpoint; retrospective paper reconstruction forbidden")
        input_start = start
        if checkpoint:
            previous_day = date.fromisoformat(checkpoint["strategy"]["last_date"])
            input_start = (previous_day + timedelta(days=1)).isoformat()
            if end < previous_day.isoformat():
                raise DataBlocked("Forward record cannot move backwards")
        data = CoreData(PolygonClient(key), input_start, end, cache_dir, allow_empty=bool(checkpoint))
        stress_config = replace(CONFIG, one_way_cost=CONFIG.one_way_cost * 2)
        if checkpoint:
            strategy, benchmark, result, periods = resume_paper(data, checkpoint)
            stress, stress_benchmark, stress_result, _ = resume_paper(data, checkpoint, stress_config, stress=True)
        else:
            strategy, benchmark, result, periods = replay(data)
            stress, stress_benchmark, stress_result, _ = replay(data, stress_config)
        if mode == "paper" and checkpoint is None and datetime.now(timezone.utc) > FIRST_PAPER_DEADLINE:
            raise DataBlocked("Initial paper intentions were not recorded before the bootstrap deadline")
        checks = gates(result)
        stress_checks = gates(stress_result)
        passed = all(item["pass"] for item in checks)
        decision.update(
            status=("PAPER_COLLECTING" if mode == "paper" and result["Periods"] < 30
                    else "PAPER_ONLY" if passed else "NO_GO"),
            historical_gates_passed=passed, metrics=result, gates=checks,
            double_cost_metrics=stress_result, double_cost_gates=stress_checks,
            input_fingerprint=data.input_fingerprint(), input_files=len(data.used_inputs),
            actual_first_session=strategy.equity[0]["date"], actual_last_session=strategy.last_date,
            unresolved_cash_claims=strategy.receivables,
            limitations=["Development history is not an untouched holdout.",
                         "No live approval; independent forward evidence is required.",
                         "Open-price fill and 15bps one-way cost are assumptions.",
                         "USD gross of tax, zero cash interest; no SEK performance claim.",
                         "Historical reference/bar revisions and ticker reuse need independent audit.",
                         "Cash merger claims without pay dates are not reinvested.",
                         "Stock-merger fractions are valued but not traded."])
        write_csv(output / "Momentum_core_daily.csv", [
            dict(row, spy_nav=other["nav"]) for row, other in zip(strategy.equity, benchmark.equity)])
        write_csv(output / "Momentum_core_trades.csv", strategy.trades)
        write_csv(output / "Momentum_core_periods.csv", periods)
        atomic_json(output / "Momentum_core_targets.json", strategy.targets)
        atomic_json(state_path, strategy.to_dict())
        atomic_json(output / "Momentum_core_inputs.json", data.used_inputs)
        atomic_json(output / "Momentum_core_paper_orders.json", {
            "model": MODEL, "as_of": strategy.last_date, "paper_only": True,
            "live_approved": False, "broker_orders_enabled": False,
            "intentions_for_next_observed_session": strategy.pending})
        atomic_json(output / "Momentum_core_data_errors.json", {"errors": []})
        if mode == "paper":
            atomic_json(checkpoint_path, {"source_fingerprint": decision["source_fingerprint"],
                        "strategy": strategy.to_dict(), "benchmark": benchmark.to_dict(),
                        "stress_strategy": stress.to_dict(), "stress_benchmark": stress_benchmark.to_dict()})
        atomic_json(decision_path, decision)
        print(json.dumps(decision, indent=2, allow_nan=False))
        return decision
    except Exception as exc:
        # requests exceptions may contain credential-bearing URLs: don't export them.
        message = re.sub(r"(?i)(apiKey=)[^&\s]+", r"\1[REDACTED]", str(exc))
        secret = os.getenv("POLYGON_API_KEY")
        if secret:
            message = message.replace(secret, "[REDACTED]")
        decision.update(status="DATA_BLOCKED", error=message,
                        error_type=type(exc).__name__, historical_gates_passed=False)
        atomic_json(output / "Momentum_core_data_errors.json", {"errors": [message]})
        atomic_json(output / "Momentum_core_paper_orders.json", {
            "status": "DATA_BLOCKED", "live_approved": False, "broker_orders_enabled": False,
            "intentions_for_next_observed_session": None, "error": message})
        atomic_json(decision_path, decision)
        print(json.dumps(decision, indent=2, allow_nan=False))
        raise DataBlocked(message) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    parser.add_argument("--output-dir", default="core_results")
    parser.add_argument("--cache-dir", default=".momentum_core_cache")
    parser.add_argument("--paper", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    try:
        run(args.start, args.end, args.output_dir, args.cache_dir,
            "paper" if args.paper else "development")
    except DataBlocked:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
