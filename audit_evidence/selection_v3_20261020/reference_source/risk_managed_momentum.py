"""Risk Managed Momentum v2: shared, causal research selection and sizing.

This module deliberately does not replace the rejected frozen v1 config or
publish trade signals. See docs/risk_managed_momentum_v2_spec.md.
"""
from dataclasses import asdict, dataclass
import math
from collections import Counter
from typing import Mapping, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RiskManagedConfig:
    model: str = "risk-managed-momentum-v2"
    position_count: int = 25
    min_raw_price: float = 10.0
    min_raw_adv20: float = 20_000_000.0
    max_volatility: float = 0.60
    max_daily_move: float = 0.25
    max_sma50_extension: float = 0.25
    max_weight: float = 0.05
    target_portfolio_volatility: float = 0.15
    stop_loss: float = 0.10
    fixed_monthly_cost: float = 0.003

    def __post_init__(self):
        positive = (self.min_raw_price, self.min_raw_adv20, self.max_volatility,
                    self.max_daily_move, self.max_sma50_extension, self.max_weight,
                    self.target_portfolio_volatility, self.stop_loss)
        if (not isinstance(self.position_count, int) or self.position_count < 1
                or any(not math.isfinite(v) or v <= 0 for v in positive)
                or self.max_weight > 1 or self.stop_loss >= 1
                or not math.isfinite(self.fixed_monthly_cost)
                or not 0 <= self.fixed_monthly_cost < 1):
            raise ValueError("Invalid risk configuration")

    def to_dict(self):
        return asdict(self)


CONFIG = RiskManagedConfig()


@dataclass(frozen=True)
class Candidate:
    ticker: str
    price: float
    raw_price: float
    raw_adv20: float
    mom12_1: float
    mom6_1: float
    mom3_1: float
    vol63: float
    vol126: float
    max_abs_daily63: float
    extension50: float
    score: float = 0.0


def row_for(day_map, ticker):
    return day_map.get(ticker) or day_map.get(ticker.replace(".", "-"))


def history_before(recent_maps, asof, count=253):
    """Reject future or disordered observations instead of trimming secretly."""
    history = list(recent_maps[:count])
    dates = [day for day, _ in history]
    if any(day > asof for day in dates) or dates != sorted(set(dates), reverse=True):
        raise ValueError("History must be unique, descending and known at the signal")
    if dates and dates[0] != asof:
        raise ValueError("History does not start at the signal session")
    return history


def close_returns(ticker, history, sessions):
    rows = [row_for(day_map, ticker) for _, day_map in history[:sessions + 1]]
    if len(rows) != sessions + 1 or any(row is None for row in rows):
        raise ValueError("Missing consecutive closes for " + ticker)
    prices = np.array([row["close"] for row in rows], dtype=float)
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Invalid close for " + ticker)
    return prices[:-1] / prices[1:] - 1.0


def spy_risk_on(recent_maps):
    if len(recent_maps) < 200:
        raise ValueError("Missing SPY SMA200 history")
    rows = [row_for(day_map, "SPY") for _, day_map in recent_maps[:200]]
    if any(row is None for row in rows):
        raise ValueError("Missing SPY observation")
    values = np.array([row["close"] for row in rows], dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Invalid SPY history")
    return bool(values[0] > values.mean())


def rank_candidates(tickers, recent_maps, asof, raw_closes, raw_dollar_volume,
                    config=CONFIG):
    """Return rankings and exclusion counts using only signal-date inputs.

    raw_dollar_volume maps session -> ticker -> observed raw close * volume.
    It must never contain a split-adjusted close multiplied by raw volume.
    No forward return, event calendar or list of historic losers is accepted.
    """
    history = history_before(recent_maps, asof)
    if len(history) < 253:
        raise ValueError("Need 253 sessions")
    rejected = Counter()
    candidates = []
    for ticker in sorted(set(tickers)):
        raw_price = raw_closes.get(ticker)
        if raw_price is None:
            rejected["missing_raw_signal_price"] += 1
            continue
        if not math.isfinite(raw_price) or raw_price < config.min_raw_price:
            rejected["raw_price_floor"] += 1
            continue
        dollars = [raw_dollar_volume.get(day, {}).get(ticker) for day, _ in history[:20]]
        if any(value is None or not math.isfinite(value) or value < 0 for value in dollars):
            rejected["missing_raw_adv20"] += 1
            continue
        adv = float(np.mean(dollars))
        if adv < config.min_raw_adv20:
            rejected["raw_liquidity_floor"] += 1
            continue
        rows = [row_for(day_map, ticker) for _, day_map in history]
        if any(row is None for row in rows):
            rejected["incomplete_formation"] += 1
            continue
        closes = np.array([row["close"] for row in rows], dtype=float)
        if not np.isfinite(closes).all() or (closes <= 0).any():
            rejected["invalid_formation"] += 1
            continue
        price = float(closes[0])
        mom = closes[21] / closes[[252, 126, 63]] - 1.0
        if (mom <= 0).any() or price <= closes[:200].mean() or closes[:200].mean() <= closes[21:221].mean():
            rejected["trend_or_momentum"] += 1
            continue
        returns = closes[:-1] / closes[1:] - 1.0
        vol63 = float(returns[:63].std(ddof=1) * np.sqrt(252))
        vol126 = float(returns[:126].std(ddof=1) * np.sqrt(252))
        if min(vol63, vol126) <= 0 or max(vol63, vol126) > config.max_volatility:
            rejected["volatility_limit"] += 1
            continue
        max_move = float(np.abs(returns[:63]).max())
        if max_move > config.max_daily_move:
            rejected["recent_daily_jump"] += 1
            continue
        extension = float(price / closes[:50].mean() - 1)
        if extension > config.max_sma50_extension:
            rejected["stretched_entry"] += 1
            continue
        candidates.append(Candidate(ticker, price, float(raw_price), adv,
                                    *map(float, mom), vol63, vol126, max_move, extension))
    if not candidates:
        return [], dict(rejected)
    frame = pd.DataFrame([asdict(row) for row in candidates])
    frame["score"] = sum(weight * (frame[field] / frame.vol126).rank(method="average", pct=True)
                         for weight, field in zip((0.5, 0.3, 0.2), ("mom12_1", "mom6_1", "mom3_1")))
    frame = frame.sort_values(["score", "ticker"], ascending=[False, True])
    return [Candidate(**row) for row in frame.to_dict("records")], dict(rejected)


def capped_inverse_volatility(volatility, budget, cap):
    """Allocate a cash budget without borrowing or exceeding any name cap."""
    vol = np.asarray(volatility, dtype=float)
    if vol.size == 0:
        return np.array([], dtype=float)
    if not np.isfinite(vol).all() or (vol <= 0).any() or not 0 <= budget <= 1 or not 0 < cap <= 1:
        raise ValueError("Invalid sizing inputs")
    remaining = min(float(budget), len(vol) * cap)
    weights = np.zeros(len(vol))
    active = list(range(len(vol)))
    while active and remaining > 1e-14:
        inverse = 1.0 / vol[active]
        proposed = remaining * inverse / inverse.sum()
        capped = [index for index, weight in zip(active, proposed) if weight >= cap]
        if not capped:
            weights[active] = proposed
            break
        for index in capped:
            weights[index] = cap
            remaining -= cap
        active = [index for index in active if index not in capped]
    return weights


def allocation(selected: Sequence[Candidate], recent_maps, asof, config=CONFIG):
    """Compute capped inverse-vol weights and an unlevered covariance target."""
    history = history_before(recent_maps, asof)
    if len(selected) > config.position_count or len({c.ticker for c in selected}) != len(selected):
        raise ValueError("Invalid selection")
    if not selected:
        return {}, {"forecast_volatility": 0.0, "scale": 0.0, "cash_weight": 1.0}
    returns = np.column_stack([close_returns(row.ticker, history, 63) for row in selected])
    vol = returns.std(axis=0, ddof=1) * np.sqrt(252)
    weights = capped_inverse_volatility(vol, len(selected) / config.position_count, config.max_weight)
    covariance = np.atleast_2d(np.cov(returns, rowvar=False, ddof=1)) * 252
    forecast = float(np.sqrt(max(0.0, weights @ covariance @ weights)))
    scale = min(1.0, config.target_portfolio_volatility / forecast) if forecast > 0 else 1.0
    weights *= scale
    if not np.isfinite(weights).all() or weights.sum() > 1 + 1e-12 or weights.max() > config.max_weight + 1e-12:
        raise AssertionError("Sizing violated cash or position limit")
    return dict(zip((row.ticker for row in selected), map(float, weights))), {
        "forecast_volatility": forecast * scale, "unscaled_forecast_volatility": forecast,
        "scale": scale, "cash_weight": 1.0 - float(weights.sum()),
    }
