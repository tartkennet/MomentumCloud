"""Broader cross-sectional momentum: rank risk instead of adding hard gates."""
from collections import Counter
from dataclasses import dataclass, replace, asdict
import math

import numpy as np
import pandas as pd

from risk_managed_momentum import Candidate, history_before, row_for


@dataclass(frozen=True)
class SelectionConfig:
    min_raw_price: float = 5.0
    min_raw_adv20: float = 2_000_000.0


CONFIG = SelectionConfig()
SELECTORS = ("broad_momentum", "broad_risk_adjusted")


def rank_candidates(tickers, recent_maps, asof, raw_closes, raw_dollar_volume):
    """Both rankings use the identical historically tradeable stock set.

    No return sign, SMA, high-volatility, price-jump or extension filter.
    Only information known by the signal close can be supplied.
    """
    history = history_before(recent_maps, asof)
    if len(history) != 253:
        raise ValueError("Need 253 consecutive signal sessions")
    excluded, raw = Counter(), []
    for ticker in sorted(set(tickers)):
        price = raw_closes.get(ticker)
        if price is None or not math.isfinite(price) or price <= 0:
            excluded["missing_or_invalid_raw_price"] += 1
            continue
        if price < CONFIG.min_raw_price:
            excluded["raw_price_floor"] += 1
            continue
        dollars = [raw_dollar_volume.get(day, {}).get(ticker) for day, _ in history[:20]]
        if any(value is None or not math.isfinite(value) or value < 0 for value in dollars):
            excluded["missing_raw_adv20"] += 1
            continue
        adv = float(np.mean(dollars))
        if adv < CONFIG.min_raw_adv20:
            excluded["raw_liquidity_floor"] += 1
            continue
        rows = [row_for(day_map, ticker) for _, day_map in history]
        if any(row is None for row in rows):
            excluded["incomplete_formation"] += 1
            continue
        closes = np.array([row["close"] for row in rows], dtype=float)
        if not np.isfinite(closes).all() or (closes <= 0).any():
            excluded["invalid_formation"] += 1
            continue
        returns = closes[:-1] / closes[1:] - 1
        vol63 = float(returns[:63].std(ddof=1) * np.sqrt(252))
        vol126 = float(returns[:126].std(ddof=1) * np.sqrt(252))
        mom = closes[21] / closes[[252, 126, 63]] - 1
        if not np.isfinite([vol63, vol126, *mom]).all() or min(vol63, vol126) <= 0:
            excluded["undefined_risk_or_momentum"] += 1
            continue
        raw.append(Candidate(ticker, float(closes[0]), float(price), adv,
                             *map(float, mom), vol63, vol126,
                             float(np.abs(returns[:63]).max()),
                             float(closes[0] / closes[:50].mean() - 1)))
    if not raw:
        return {name: [] for name in SELECTORS}, dict(excluded)
    frame = pd.DataFrame([asdict(candidate) for candidate in raw])
    ranks = {}
    for selector in SELECTORS:
        scale = frame.vol126 if selector == "broad_risk_adjusted" else 1.0
        score = sum(weight * (frame[field] / scale).rank(method="average", pct=True)
                    for weight, field in zip((.5, .3, .2), ("mom12_1", "mom6_1", "mom3_1")))
        ranked = frame.assign(score=score).sort_values(["score", "ticker"], ascending=[False, True])
        ranks[selector] = [Candidate(**row) for row in ranked.to_dict("records")]
    if {c.ticker for c in ranks[SELECTORS[0]]} != {c.ticker for c in ranks[SELECTORS[1]]}:
        raise AssertionError("Selectors do not share their eligible set")
    return ranks, dict(excluded)
