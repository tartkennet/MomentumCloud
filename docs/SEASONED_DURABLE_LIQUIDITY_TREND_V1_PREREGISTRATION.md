# Seasoned Durable Liquidity Trend v1 — preregistration

**Status:** Registered before the first run. This is a new candidate, not a parameter adjustment of any rejected model.

## Hypothesis

A cross-sectional trend model may be more robust when it selects only seasoned, persistently liquid stocks and ranks trend relative to recent realized volatility. It does not reuse the prior 12–1/6–1/3–1 score, regression score, breakout, per-stock SMA filter, beta adjustment, or stop-loss rules.

## Point-in-time universe

- U.S.-listed common stocks from the point-in-time reference universe; exclude ETFs, ADRs, warrants and preferred shares.
- At least **504 completed trading sessions** at the signal date. This is a pre-specified seasoning rule, not a ticker exclusion.
- Signal-date close above $5.
- Both 20-session and 126-session average daily dollar volume at least $2,000,000.
- No manual ticker exclusions and no use of future corporate actions, delistings or outcomes in selection.

## Signal and portfolio

- At month-end, require close above SMA200, SMA50 above SMA200, and positive 126-session total return.
- Rank eligible stocks by: 126-session total return divided by annualized standard deviation of the preceding 63 daily close-to-close returns.
- Hold the top 12, equal weighted.
- Rebalance monthly; form the signal at month-end and execute at the next session's open.
- SPY above its completed-session SMA200 is RISK ON. Otherwise hold 100% cash.
- No discretionary stop-loss.

## Execution and validation

- Backtest request remains 2023-02-01 through the available end date. The report must state the first executable signal date after the 504-session requirement.
- Use only point-in-time inputs, adjusted historical bars, next-open execution, documented transaction costs and slippage.
- Out-of-sample starts 2025-03-31. It must contain at least 12 monthly periods.
- Daily marked-to-market equity is used for maximum drawdown.
- Any held security with no executable exit price and no verified cash/corporate-action settlement makes the candidate **non-evaluable and NO-GO**. No last-price, zero-price, or synthetic settlement is allowed.

## Approval gates

Both total period and OOS must have positive net return, beat SPY, maximum drawdown no worse than 20%, and hit rate at least 50%; OOS must have at least 12 periods. Otherwise the candidate is **EJ GODKÄND FÖR KÖP**.

## Scope lock

This research candidate must not change Buy Now, the production model, the app, real orders, automatic trading, or the fictional portfolio unless every approval gate passes.

Current limitation: survivorship bias
