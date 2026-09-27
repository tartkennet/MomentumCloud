"""Frozen configuration for the liquid-leaders validation candidate.

The model ranks independently gated US trend leaders by relative strength,
trend efficiency and trading liquidity. It is a validation candidate until
the point-in-time gate approves it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionConfig:
    product_name: str = "MomentumCloud Liquid Leaders"
    selection_model: str = "liquid-leaders-v1"
    position_count: int = 15
    candidate_count: int = 50
    min_price_usd: float = 10.0
    min_adv20_usd: float = 5_000_000.0
    stop_loss_pct: float = 10.0
    trend_lookback_sessions: int = 252
    minimum_positive_months: int = 7
    max_annualized_volatility_pct: float = 40.0
    max_extension_sma50_pct: float = 15.0
    eligible_security_types: tuple[str, ...] = ("CS",)
    eligible_primary_exchanges: tuple[str, ...] = ("XNAS", "XNYS", "XASE")
    rebalance_frequency: str = "monthly"
    market_regime: str = "SPY > SMA200"
    limitation: str = "Current limitation: survivorship bias"

    def validate(self) -> None:
        if self.selection_model != "liquid-leaders-v1":
            raise ValueError("Production selection_model must be liquid-leaders-v1")
        if self.position_count != 15:
            raise ValueError("Production portfolio must contain 15 positions")
        if self.min_price_usd != 10.0:
            raise ValueError("Production minimum price must be exactly 10 USD")
        if self.min_adv20_usd != 5_000_000.0:
            raise ValueError("Production ADV20 minimum must be exactly 5,000,000 USD")
        if self.stop_loss_pct != 10.0:
            raise ValueError("Production stop loss must be exactly 10 percent")
        if self.trend_lookback_sessions != 252:
            raise ValueError("Trend formation window must be exactly 252 sessions")
        if self.minimum_positive_months != 7:
            raise ValueError("Trend persistence must require exactly 7 positive months")
        if self.max_annualized_volatility_pct != 40.0:
            raise ValueError("Maximum volatility must be exactly 40 percent")
        if self.max_extension_sma50_pct != 15.0:
            raise ValueError("Maximum SMA50 extension must be exactly 15 percent")
        if self.market_regime != "SPY > SMA200":
            raise ValueError("Production market regime must be SPY > SMA200")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


PRODUCTION = ProductionConfig()
PRODUCTION.validate()
