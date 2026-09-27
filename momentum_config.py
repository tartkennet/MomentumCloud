"""Frozen configuration for the robust cross-sectional validation candidate.

This is deliberately a simple model: established price trend plus standard
12-1, 6-1 and 3-1 cross-sectional momentum. It remains a validation
candidate until it passes the point-in-time gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionConfig:
    product_name: str = "MomentumCloud Robust Momentum"
    selection_model: str = "robust-momentum-v1"
    position_count: int = 15
    candidate_count: int = 50
    min_price_usd: float = 5.0
    min_adv20_usd: float = 2_000_000.0
    stop_loss_pct: float = 10.0
    trend_lookback_sessions: int = 252
    weight_rank_12_1: float = 0.50
    weight_rank_6_1: float = 0.30
    weight_rank_3_1: float = 0.20
    eligible_security_types: tuple[str, ...] = ("CS",)
    eligible_primary_exchanges: tuple[str, ...] = ("XNAS", "XNYS", "XASE")
    rebalance_frequency: str = "monthly"
    market_regime: str = "SPY > SMA200"
    limitation: str = "Current limitation: survivorship bias"

    def validate(self) -> None:
        if self.selection_model != "robust-momentum-v1":
            raise ValueError("Production selection_model must be robust-momentum-v1")
        if self.position_count != 15:
            raise ValueError("Production portfolio must contain 15 positions")
        if self.min_price_usd != 5.0:
            raise ValueError("Production minimum price must be exactly 5 USD")
        if self.min_adv20_usd != 2_000_000.0:
            raise ValueError("Production ADV20 minimum must be exactly 2,000,000 USD")
        if self.stop_loss_pct != 10.0:
            raise ValueError("Production stop loss must be exactly 10 percent")
        if self.trend_lookback_sessions != 252:
            raise ValueError("Trend formation window must be exactly 252 sessions")
        if (
            self.weight_rank_12_1 != 0.50
            or self.weight_rank_6_1 != 0.30
            or self.weight_rank_3_1 != 0.20
        ):
            raise ValueError("Momentum ranking weights must be fixed at 50/30/20")
        if self.market_regime != "SPY > SMA200":
            raise ValueError("Production market regime must be SPY > SMA200")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


PRODUCTION = ProductionConfig()
PRODUCTION.validate()
