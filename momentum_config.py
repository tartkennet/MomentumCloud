"""Locked configuration for MomentumCloud Production v1.

This module is deliberately boring: production rules live in one place and
cannot be changed from a workflow input.  Research models remain available in
the historical backtest module, but the application imports only this file.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionConfig:
    product_name: str = "MomentumCloud Production v1"
    selection_model: str = "fresh-momentum-1-3m"
    position_count: int = 15
    candidate_count: int = 50
    min_price_usd: float = 10.0
    min_adv20_usd: float = 5_000_000.0
    stop_loss_pct: float = 10.0
    weight_rank_1m: float = 0.30
    weight_rank_3m: float = 0.40
    weight_rank_6m: float = 0.15
    weight_low_volatility: float = 0.10
    weight_low_extension: float = 0.05
    min_return_1m_pct: float = 0.0
    min_return_3m_pct: float = 0.0
    min_relative_1m_pct: float = 0.0
    min_relative_3m_pct: float = 0.0
    max_volatility_pct: float = 80.0
    max_extension_sma50_pct: float = 20.0
    eligible_security_types: tuple[str, ...] = ("CS",)
    eligible_primary_exchanges: tuple[str, ...] = ("XNAS", "XNYS", "XASE")
    rebalance_frequency: str = "monthly"
    market_regime: str = "SPY > SMA200"
    limitation: str = "Current limitation: survivorship bias"

    def validate(self) -> None:
        if self.selection_model != "fresh-momentum-1-3m":
            raise ValueError("Production selection_model must be fresh-momentum-1-3m")
        if self.position_count != 15:
            raise ValueError("Production portfolio must contain 15 positions")
        if self.min_price_usd != 10.0:
            raise ValueError("Production minimum price must be exactly 10 USD")
        if self.min_adv20_usd != 5_000_000.0:
            raise ValueError("Production ADV20 minimum must be exactly 5,000,000 USD")
        if self.stop_loss_pct != 10.0:
            raise ValueError("Production stop loss must be exactly 10 percent")
        weights = (
            self.weight_rank_1m,
            self.weight_rank_3m,
            self.weight_rank_6m,
            self.weight_low_volatility,
            self.weight_low_extension,
        )
        if abs(sum(weights) - 1.0) > 1e-12:
            raise ValueError("Production ranking weights must sum to one")
        if self.max_volatility_pct != 80.0:
            raise ValueError("Production volatility cap must be exactly 80 percent")
        if self.max_extension_sma50_pct != 20.0:
            raise ValueError("Production SMA50 extension cap must be exactly 20 percent")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


PRODUCTION = ProductionConfig()
PRODUCTION.validate()
