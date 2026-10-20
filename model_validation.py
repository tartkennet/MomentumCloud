"""Single source of truth for production-model approval.

A candidate list is not an approved investment strategy.  Production may expose
research candidates, but actionable Buy Now output requires a persisted,
point-in-time validation decision for the exact locked model.
"""
from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path

from momentum_config import PRODUCTION

VALIDATION_DECISION_FILE = Path("Momentum_validation_decision.json")
REQUIRED_GATES = (
    "at_least_30_periods",
    "positive_net_return",
    "beats_spy",
    "daily_max_drawdown_at_most_20_pct",
    "hit_rate_at_least_50_pct",
)
VALIDATION_SOURCE_FILES = (
    "momentum_config.py", "momentum_strategy.py", "momentum_production.py",
    "momentum_master_v3.py", "backtest_momentum_v3.py",
    "validate_production_backtest.py", "model_validation.py",
    "requirements.txt", "Momentum mall fil.xlsx",
)


def validation_source_fingerprint(root: Path | None = None) -> str:
    """Bind a decision to model, execution, consumer and universe-input bytes."""
    root = root or Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in VALIDATION_SOURCE_FILES:
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256((root / name).read_bytes()).digest())
    return digest.hexdigest()


def evaluate_metrics(metrics: dict) -> dict:
    """The existing five performance gates, with no parameter changes."""
    names = (
        "Periods", "TotalReturn_pct", "SPYTotalReturn_pct",
        "TotalEdgeVsSPY_pct", "DailyMaxDrawdown_pct", "PeriodHitRate_pct",
    )
    values = {name: float(metrics[name]) for name in names}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("Validation metrics must be finite")
    if not math.isclose(
        values["TotalEdgeVsSPY_pct"],
        values["TotalReturn_pct"] - values["SPYTotalReturn_pct"],
        rel_tol=1e-9, abs_tol=1e-8,
    ):
        raise ValueError("Validation edge is inconsistent with strategy and SPY returns")
    return {
        "at_least_30_periods": int(values["Periods"]) >= 30,
        "positive_net_return": values["TotalReturn_pct"] > 0.0,
        "beats_spy": values["TotalEdgeVsSPY_pct"] > 0.0,
        "daily_max_drawdown_at_most_20_pct": values["DailyMaxDrawdown_pct"] >= -20.0,
        "hit_rate_at_least_50_pct": values["PeriodHitRate_pct"] >= 50.0,
    }


def load_model_validation(path: Path = VALIDATION_DECISION_FILE) -> dict:
    """Read only a complete GO decision for the current locked configuration."""
    base = {
        "approved": False,
        "status": "UNVALIDATED",
        "reason": "No verified point-in-time validation decision is published.",
        "model": PRODUCTION.selection_model,
        "gates": {gate: False for gate in REQUIRED_GATES},
    }
    try:
        decision = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return base
    if not isinstance(decision, dict):
        return base

    gates = decision.get("gates")
    model = decision.get("model")
    universe = decision.get("universe")
    complete_gates = isinstance(gates, dict) and all(gates.get(gate) is True for gate in REQUIRED_GATES)
    metrics = decision.get("metrics")
    try:
        calculated_gates = evaluate_metrics(metrics) if isinstance(metrics, dict) else {}
        matches_source = decision.get("source_fingerprint") == validation_source_fingerprint()
    except (OSError, KeyError, TypeError, ValueError, OverflowError):
        calculated_gates, matches_source = {}, False
    verified_metrics = bool(calculated_gates) and calculated_gates == gates
    approved = bool(
        decision.get("status") == "GO"
        and model == PRODUCTION.selection_model
        and universe == "POINT_IN_TIME_US_COMMON_STOCKS"
        and complete_gates
        and matches_source
        and verified_metrics
    )
    return {
        "approved": approved,
        "status": "APPROVED" if approved else (
            "UNVALIDATED" if decision.get("status") == "GO"
            else str(decision.get("status") or "UNVALIDATED")
        ),
        "reason": (
            "Verified point-in-time validation passed all locked production gates."
            if approved
            else str(decision.get("error") or "Model is research-only until matching source and verified metrics pass every gate.")
        ),
        "model": model or PRODUCTION.selection_model,
        "universe": universe,
        "gates": {gate: bool(gates.get(gate)) if isinstance(gates, dict) else False for gate in REQUIRED_GATES},
        "metrics": metrics if isinstance(metrics, dict) else {},
        "validated_at": decision.get("validated_at"),
        "source_fingerprint": decision.get("source_fingerprint"),
        "source_matches": matches_source,
    }
