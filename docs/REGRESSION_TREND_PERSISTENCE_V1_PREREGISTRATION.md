# Regression Trend Persistence v1, preregistration

## Purpose
A single replacement candidate for PR 13 after trend-pullback-v1 was verified NO-GO. This is a new hypothesis, not a revision of a rejected momentum, breakout, liquidity, beta-adjusted, or pullback model.

## Hypothesis
A persistent linear price trend is different from a raw return or moving-average signal. A stock whose completed 100-session log-price path has both a positive slope and a high fit to a straight line may be a more reliable momentum holding than a stock selected by raw 12/6/3-month returns.

## Fixed rules before the run
- Point-in-time US-listed common-stock universe only. Exclude ETFs, ADRs, warrants and preferred shares.
- Price above 5 USD, ADV20 at least 2,000,000 USD, and at least 252 completed trading sessions.
- Signal at each month-end, execution at the next market open. Monthly rebalance.
- Market gate: SPY close above its completed SMA200. Otherwise 100% cash.
- For each eligible stock, fit ordinary least squares to the completed 100 most recent daily log closes. Compute the annualised fitted slope and R-squared.
- Require a positive annualised fitted slope. Rank stocks by annualised fitted slope multiplied by R-squared.
- Hold the 10 highest-ranked stocks equally weighted.
- No stock-level SMA filter, no raw 12/6/3 momentum score, no beta adjustment, no breakout or extension rule, and no stop loss. Every position exits only at the next monthly rebalance.
- Apply the existing round-trip cost and slippage assumptions. No look-ahead.

## Locked validation
Start 2023-02-01. Untouched OOS starts 2025-03-31. A GO requires both total and OOS: positive net return, beating SPY, daily maximum drawdown no worse than 20%, and hit rate at least 50%. OOS must contain at least 12 periods.

## Scope safeguards
No real orders, automatic trading, Buy Now, production model, or paper portfolio changes. Rejected models are not reused.

Current limitation: survivorship bias
