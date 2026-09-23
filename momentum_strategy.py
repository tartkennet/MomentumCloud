"""Pure, deterministic production strategy for MomentumCloud.

Prices are expected newest first.  Signals are formed from adjusted daily
OHLCV rows.  The module performs no network or file I/O, which keeps the
locked strategy independently testable.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

import pandas as pd

from momentum_config import PRODUCTION, ProductionConfig


@dataclass(frozen=True)
class Security:
    ticker: str
    name: str = ""
    security_type: str = "CS"
    primary_exchange: str = ""
    active: bool = True


@dataclass(frozen=True)
class MomentumMetric:
    ticker: str
    price_usd: float
    adv20_usd: float
    sma20: float
    sma50: float
    sma50_1m_ago: float
    sma200: float
    sma200_1m_ago: float
    return_1m_pct: float
    return_3m_pct: float
    return_6m_pct: float
    spy_return_1m_pct: float
    spy_return_3m_pct: float
    relative_1m_pct: float
    relative_3m_pct: float
    volatility_pct: float
    extension_sma50_pct: float
    score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def is_eligible_security(security: Security, config: ProductionConfig = PRODUCTION) -> bool:
    """Exclude non-common stocks, ADRs, preferreds, ETFs and likely SPACs."""
    name = security.name.upper()
    spac_markers = ("ACQUISITION", "BLANK CHECK", " SPAC", "ACQUISITION CORP")
    return bool(
        security.active
        and security.security_type in config.eligible_security_types
        and security.primary_exchange in config.eligible_primary_exchanges
        and not any(marker in name for marker in spac_markers)
    )


def _row(day_map: Mapping[str, Mapping[str, float]], ticker: str):
    ticker = ticker.upper().strip()
    return day_map.get(ticker) or day_map.get(ticker.replace(".", "-"))


def market_regime(recent_maps: Sequence[tuple[str, Mapping]]) -> dict:
    """Return the locked SPY>SMA200 regime; missing data fails safely to cash."""
    closes = []
    for _, day_map in recent_maps:
        row = _row(day_map, "SPY")
        if not row:
            break
        closes.append(float(row["close"]))
    if len(closes) < 200:
        return {
            "status": "RISK OFF",
            "risk_on": False,
            "spy_close": closes[0] if closes else None,
            "spy_sma200": None,
            "reason": "Insufficient SPY history",
        }
    sma200 = sum(closes[:200]) / 200.0
    risk_on = closes[0] > sma200
    return {
        "status": "RISK ON" if risk_on else "RISK OFF",
        "risk_on": risk_on,
        "spy_close": closes[0],
        "spy_sma200": sma200,
        "reason": "SPY above SMA200" if risk_on else "SPY at or below SMA200",
    }


def _raw_metric(
    ticker: str,
    recent_maps: Sequence[tuple[str, Mapping]],
    config: ProductionConfig,
    spy_return_1m: float,
    spy_return_3m: float,
) -> MomentumMetric | None:
    closes: list[float] = []
    dollar_volume: list[float] = []
    for index, (_, day_map) in enumerate(recent_maps):
        row = _row(day_map, ticker)
        if not row:
            break
        close = float(row["close"])
        volume = row.get("volume")
        if not math.isfinite(close) or close <= 0:
            return None
        closes.append(close)
        if index < 20 and volume is not None:
            volume = float(volume)
            if not math.isfinite(volume) or volume < 0:
                return None
            dollar_volume.append(close * volume)

    if len(closes) < 253 or len(dollar_volume) < 20:
        return None
    # Adjusted Polygon closes should not contain split-sized discontinuities.
    # Fail closed instead of allowing a corrupt series to dominate momentum.
    adjacent_ratios = [
        max(newer, older) / min(newer, older)
        for newer, older in zip(closes, closes[1:])
    ]
    if max(adjacent_ratios, default=1.0) >= 3.0:
        return None

    price = closes[0]
    adv20 = sum(dollar_volume) / 20.0
    sma20 = sum(closes[:20]) / 20.0
    sma50 = sum(closes[:50]) / 50.0
    sma50_1m_ago = sum(closes[21:71]) / 50.0
    sma200 = sum(closes[:200]) / 200.0
    sma200_1m_ago = sum(closes[21:221]) / 200.0
    return_1m = (price / closes[21] - 1.0) * 100.0
    return_3m = (price / closes[63] - 1.0) * 100.0
    return_6m = (price / closes[126] - 1.0) * 100.0
    relative_1m = return_1m - spy_return_1m
    relative_3m = return_3m - spy_return_3m

    chronological = list(reversed(closes[21:127]))
    returns = [
        later / earlier - 1.0
        for earlier, later in zip(chronological, chronological[1:])
        if earlier > 0 and later > 0
    ]
    if len(returns) < 80:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    volatility = math.sqrt(max(variance, 0.0)) * math.sqrt(252.0) * 100.0
    extension = (price / sma50 - 1.0) * 100.0

    if (
        price < config.min_price_usd
        or adv20 < config.min_adv20_usd
        or price <= sma20
        or sma20 <= sma50
        or price <= sma200
        or sma50 <= sma50_1m_ago
        or sma200 <= sma200_1m_ago
        or return_1m <= config.min_return_1m_pct
        or return_3m <= config.min_return_3m_pct
        or return_6m <= 0.0
        or relative_1m <= config.min_relative_1m_pct
        or relative_3m <= config.min_relative_3m_pct
        or volatility > config.max_volatility_pct
        or extension > config.max_extension_sma50_pct
    ):
        return None
    return MomentumMetric(
        ticker=ticker,
        price_usd=price,
        adv20_usd=adv20,
        sma20=sma20,
        sma50=sma50,
        sma50_1m_ago=sma50_1m_ago,
        sma200=sma200,
        sma200_1m_ago=sma200_1m_ago,
        return_1m_pct=return_1m,
        return_3m_pct=return_3m,
        return_6m_pct=return_6m,
        spy_return_1m_pct=spy_return_1m,
        spy_return_3m_pct=spy_return_3m,
        relative_1m_pct=relative_1m,
        relative_3m_pct=relative_3m,
        volatility_pct=volatility,
        extension_sma50_pct=extension,
    )


def rank_universe(
    tickers: Iterable[str],
    recent_maps: Sequence[tuple[str, Mapping]],
    config: ProductionConfig = PRODUCTION,
) -> list[MomentumMetric]:
    """Return quality-momentum names ranked by relative strength and risk."""
    config.validate()
    spy_closes = []
    for _, day_map in recent_maps:
        row = _row(day_map, "SPY")
        if not row:
            break
        close = float(row["close"])
        if not math.isfinite(close) or close <= 0:
            return []
        spy_closes.append(close)
    if len(spy_closes) < 64:
        return []
    spy_return_1m = (spy_closes[0] / spy_closes[21] - 1.0) * 100.0
    spy_return_3m = (spy_closes[0] / spy_closes[63] - 1.0) * 100.0
    raw = [
        metric
        for ticker in dict.fromkeys(str(value).upper().strip() for value in tickers)
        if ticker
        for metric in [
            _raw_metric(
                ticker, recent_maps, config, spy_return_1m, spy_return_3m
            )
        ]
        if metric is not None
    ]
    if not raw:
        return []
    frame = pd.DataFrame([item.to_dict() for item in raw])
    frame["rank_1m"] = frame["relative_1m_pct"].rank(method="average", pct=True)
    frame["rank_3m"] = frame["relative_3m_pct"].rank(method="average", pct=True)
    frame["rank_6m"] = frame["return_6m_pct"].rank(method="average", pct=True)
    frame["rank_low_volatility"] = frame["volatility_pct"].rank(
        method="average", ascending=False, pct=True
    )
    frame["rank_low_extension"] = frame["extension_sma50_pct"].rank(
        method="average", ascending=False, pct=True
    )
    frame["score"] = 100.0 * (
        config.weight_rank_1m * frame["rank_1m"]
        + config.weight_rank_3m * frame["rank_3m"]
        + config.weight_rank_6m * frame["rank_6m"]
        + config.weight_low_volatility * frame["rank_low_volatility"]
        + config.weight_low_extension * frame["rank_low_extension"]
    )
    frame = frame.sort_values(["score", "ticker"], ascending=[False, True])
    fields = tuple(MomentumMetric.__dataclass_fields__)
    return [
        MomentumMetric(**{field: row[field] for field in fields})
        for row in frame.to_dict(orient="records")
    ]


def build_target_portfolio(
    ranked: Sequence[MomentumMetric],
    risk_on: bool,
    portfolio_value_sek: float | None = None,
    usdsek: float | None = None,
    config: ProductionConfig = PRODUCTION,
) -> list[dict]:
    if not risk_on:
        return []
    if (portfolio_value_sek is None) != (usdsek is None):
        raise ValueError("portfolio_value_sek and usdsek must be supplied together")
    if portfolio_value_sek is not None and (portfolio_value_sek <= 0 or usdsek <= 0):
        raise ValueError("Portfolio value and USDSEK must be positive")

    weight = 1.0 / config.position_count
    position_value_sek = (
        portfolio_value_sek * weight if portfolio_value_sek is not None else None
    )
    target = []
    for model_rank, metric in enumerate(ranked, 1):
        quantity = None
        if position_value_sek is not None:
            quantity = math.floor(position_value_sek / (metric.price_usd * usdsek))
            if quantity < 1:
                continue
        target.append(
            {
                "rank": model_rank,
                "target_rank": len(target) + 1,
                **metric.to_dict(),
                "weight_pct": weight * 100.0,
                "quantity": quantity,
                "buy_signal": "BUY",
            }
        )
        if len(target) == config.position_count:
            break

    if len(target) != config.position_count:
        raise RuntimeError(
            f"Only {len(target)} whole-share positions are affordable; "
            f"{config.position_count} are required"
        )
    return target


def stop_is_triggered(current_price: float, adjusted_entry_price: float) -> bool:
    if current_price <= 0 or adjusted_entry_price <= 0:
        raise ValueError("Prices must be positive")
    return current_price <= adjusted_entry_price * (1.0 - PRODUCTION.stop_loss_pct / 100.0)
