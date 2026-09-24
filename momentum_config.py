"""Locked configuration for MomentumCloud Production v1.

Production uses exactly one model. Research-only legacy models may remain in
historical comparison code, but no workflow input can change these rules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionConfig:
    product_name: str = "MomentumCloud Production v1"
    selection_model: str = "v4-balanced"
    position_count: int = 15
    candidate_count: int = 50
    min_price_usd: float = 10.0
    min_adv20_usd: float = 5_000_000.0
    stop_loss_pct: float = 10.0
    weight_rank_12_2: float = 0.55
    weight_rank_6_2: float = 0.20
    weight_low_volatility: float = 0.15
    weight_low_extension: float = 0.10
    eligible_security_types: tuple[str, ...] = ("CS",)
    eligible_primary_exchanges: tuple[str, ...] = ("XNAS", "XNYS", "XASE")
    rebalance_frequency: str = "monthly"
    market_regime: str = "SPY > SMA200"
    limitation: str = "Current limitation: survivorship bias"

    def validate(self) -> None:
        if self.selection_model != "v4-balanced":
            raise ValueError("Production selection_model must be v4-balanced")
        if self.position_count != 15:
            raise ValueError("Production portfolio must contain 15 positions")
        if self.min_price_usd != 10.0:
            raise ValueError("Production minimum price must be exactly 10 USD")
        if self.min_adv20_usd != 5_000_000.0:
            raise ValueError("Production ADV20 minimum must be exactly 5,000,000 USD")
        if self.stop_loss_pct != 10.0:
            raise ValueError("Production stop loss must be exactly 10 percent")
        weights = (
            self.weight_rank_12_2,
            self.weight_rank_6_2,
            self.weight_low_volatility,
            self.weight_low_extension,
        )
        if weights != (0.55, 0.20, 0.15, 0.10):
            raise ValueError("Production v4-balanced ranking weights are locked")
        if abs(sum(weights) - 1.0) > 1e-12:
            raise ValueError("Production ranking weights must sum to one")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


PRODUCTION = ProductionConfig()
PRODUCTION.validate()
