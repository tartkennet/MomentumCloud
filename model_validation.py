"""Single source of truth for production-model approval.

A candidate list is not an approved investment strategy.  Production may expose
research candidates, but actionable Buy Now output requires a persisted,
point-in-time validation decision for the exact locked model.
"""
from __future__ import annotations

import json
from pathlib import Path

from momentum_config import PRODUCTION

VALIDATION_DECISION_FILE = Path("Momentum_validation_decision.json")
REQUIRED_GATES = (
    "at_least_30_periods",
    "positive_net_return",
    "beats_spy",
    "daily_max_drawdown_at_most_20_pct",
    "hit_rate_at_least_50_pct",
    "oos_at_least_12_periods",
    "oos_positive_net_return",
    "oos_beats_spy",
    "oos_hit_rate_at_least_50_pct",
)


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
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return base

    gates = decision.get("gates")
    model = decision.get("model")
    universe = decision.get("universe")
    complete_gates = isinstance(gates, dict) and all(gates.get(gate) is True for gate in REQUIRED_GATES)
    approved = bool(
        decision.get("status") == "GO"
        and model == PRODUCTION.selection_model
        and universe == "POINT_IN_TIME_US_COMMON_STOCKS"
        and complete_gates
    )
    return {
        "approved": approved,
        "status": "APPROVED" if approved else str(decision.get("status") or "UNVALIDATED"),
        "reason": (
            "Verified point-in-time validation passed all locked production gates."
            if approved
            else "Model is research-only until the exact locked point-in-time validation passes every gate."
        ),
        "model": model or PRODUCTION.selection_model,
        "universe": universe,
        "gates": {gate: bool(gates.get(gate)) if isinstance(gates, dict) else False for gate in REQUIRED_GATES},
        "metrics": decision.get("metrics", {}),
        "validated_at": decision.get("validated_at"),
    }
