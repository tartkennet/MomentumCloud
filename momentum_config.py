"""Locked configuration for MomentumCloud Production v1.

Production uses exactly one model. Research-only legacy models may remain in
historical comparison code, but no workflow input can change these rules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionConfig:
    product_name: str = "MomentumCloud Production v1"
    selection_model: str = "core-momentum-v1"
    position_count: int = 12
    candidate_count: int = 50
    min_price_usd: float = 5.0
    min_adv20_usd: float = 5_000_000.0
    stop_loss_pct: float = 10.0
    weight_rank_12_2: float = 0.50
    weight_rank_6_2: float = 0.30
    weight_rank_3m: float = 0.20
    rank_exit_cutoff: int = 20
    eligible_security_types: tuple[str, ...] = ("CS",)
    eligible_primary_exchanges: tuple[str, ...] = ("XNAS", "XNYS", "XASE")
    rebalance_frequency: str = "monthly"
    market_regime: str = "SPY > SMA200"
    limitation: str = "Current limitation: survivorship bias"

    def validate(self) -> None:
        if self.selection_model != "core-momentum-v1":
            raise ValueError("Production selection_model must be core-momentum-v1")
        if self.position_count != 12:
            raise ValueError("Production portfolio must contain 12 positions")
        if self.min_price_usd != 5.0:
            raise ValueError("Production minimum price must be exactly 5 USD")
        if self.min_adv20_usd != 5_000_000.0:
            raise ValueError("Production ADV20 minimum must be exactly 5,000,000 USD")
        if self.stop_loss_pct != 10.0:
            raise ValueError("Production stop loss must be exactly 10 percent")
        weights = (self.weight_rank_12_2, self.weight_rank_6_2, self.weight_rank_3m)
        if weights != (0.50, 0.30, 0.20):
            raise ValueError("Production core-momentum-v1 ranking weights are locked")
        if abs(sum(weights) - 1.0) > 1e-12:
            raise ValueError("Production ranking weights must sum to one")
        if self.rank_exit_cutoff != 20:
            raise ValueError("Production rank exit cutoff must be exactly 20")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


PRODUCTION = ProductionConfig()
PRODUCTION.validate()
