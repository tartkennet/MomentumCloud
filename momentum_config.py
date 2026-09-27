"""Frozen configuration for the relative-strength breakout candidate.

This candidate deliberately replaces the old weighted 12-2/6-2 momentum
formula.  It must not be released until a separate point-in-time validation
passes every gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionConfig:
    product_name: str = "MomentumCloud Relative Strength Breakout"
    selection_model: str = "relative-strength-breakout-v1"
    position_count: int = 12
    candidate_count: int = 50
    min_price_usd: float = 5.0
    min_adv20_usd: float = 5_000_000.0
    stop_loss_pct: float = 10.0
    relative_strength_lookback_sessions: int = 126
    breakout_lookback_sessions: int = 252
    minimum_breakout_fraction: float = 0.90
    max_annualized_volatility_pct: float = 60.0
    max_extension_sma50_pct: float = 25.0
    eligible_security_types: tuple[str, ...] = ("CS",)
    eligible_primary_exchanges: tuple[str, ...] = ("XNAS", "XNYS", "XASE")
    rebalance_frequency: str = "monthly"
    market_regime: str = "SPY > SMA200 and SPY SMA50 > SMA200"
    limitation: str = "Current limitation: survivorship bias"

    def validate(self) -> None:
        if self.selection_model != "relative-strength-breakout-v1":
            raise ValueError("Production selection_model must be relative-strength-breakout-v1")
        if self.position_count != 12:
            raise ValueError("Production portfolio must contain 12 positions")
        if self.min_price_usd != 5.0:
            raise ValueError("Production minimum price must be exactly 5 USD")
        if self.min_adv20_usd != 5_000_000.0:
            raise ValueError("Production ADV20 minimum must be exactly 5,000,000 USD")
        if self.stop_loss_pct != 10.0:
            raise ValueError("Production stop loss must be exactly 10 percent")
        if self.relative_strength_lookback_sessions != 126:
            raise ValueError("Relative strength lookback must be exactly 126 sessions")
        if self.breakout_lookback_sessions != 252:
            raise ValueError("Breakout lookback must be exactly 252 sessions")
        if self.minimum_breakout_fraction != 0.90:
            raise ValueError("Breakout threshold must be exactly 90 percent of the 252-session high")
        if self.max_annualized_volatility_pct != 60.0:
            raise ValueError("Maximum volatility must be exactly 60 percent")
        if self.max_extension_sma50_pct != 25.0:
            raise ValueError("Maximum SMA50 extension must be exactly 25 percent")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


PRODUCTION = ProductionConfig()
PRODUCTION.validate()
