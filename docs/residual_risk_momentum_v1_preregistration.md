# Residual Risk Momentum v1, preregistration

## Purpose
A single replacement candidate for PR 13 after trend-pullback-v1 was verified NO-GO. This is a new hypothesis, not a parameter revision of any rejected model.

## Hypothesis
Stocks with positive six-month return after removing their realised SPY beta exposure can deliver cross-sectional momentum. Volatility-scaled position sizes and a market-wide risk gate may improve drawdown control without requiring per-stock moving averages, raw 12/6/3-month momentum confirmation, breakouts, extension filters, or stop-loss exits.

## Fixed rules before the run
- Point-in-time US-listed common-stock universe only. Exclude ETFs, ADRs, warrants and preferred shares.
- Price above 5 USD, ADV20 at least 2,000,000 USD, and at least 252 completed trading sessions.
- Signal at each month-end, execution at the next market open. Monthly rebalance.
- Market gate: SPY close above its completed SMA200. Otherwise 100% cash.
- For each eligible stock, compute daily returns over the completed 126-session window. Estimate beta to SPY from paired daily returns. Residual 6-month return = stock 126-session return minus beta times SPY 126-session return.
- Require positive residual 6-month return. Rank by residual 6-month return divided by realised annualised stock volatility over the same completed window.
- Hold the 10 highest-ranked stocks. Weight by inverse realised volatility, normalized to 100%.
- No stock-level SMA filter, no raw 12/6/3 momentum score, no breakout or extension rule, and no stop loss. Every position exits only at the next monthly rebalance.
- Apply the existing round-trip cost and slippage assumptions. No look-ahead.

## Locked validation
Start 2023-02-01. Untouched OOS starts 2025-03-31. A GO requires both total and OOS: positive net return, beating SPY, daily maximum drawdown no worse than 20%, and hit rate at least 50%. OOS must contain at least 12 periods.

## Scope safeguards
No real orders, automatic trading, Buy Now, production model, or paper portfolio changes. Rejected models are not reused.

Current limitation: survivorship bias
