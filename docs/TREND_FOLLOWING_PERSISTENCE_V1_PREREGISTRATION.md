# Trend-following persistence 252 v1: pre-registration

Status: one-shot candidate following the verified NO-GO of PR 13's
`seasoned-durable-liquidity-trend-v1`. This is a different model family: it
does not rank 12-1, 6-1 or 3-1 returns, does not use beta-adjusted returns,
and does not use a fixed percentage stop.

This replaces the unexecuted 504-session specification. That specification
could not request the required 2021 history from Massive Starter when the
test starts in February 2023, and therefore produced no backtest results.
This change is made before any result exists and solely to fit the known
five-year data entitlement; it is not calibrated to returns or drawdown.

## Fixed rules before the run

- Universe: point-in-time US-listed common stocks only. ETFs, ADRs, warrants
  and preferred shares are excluded by the security master.
- Eligibility: closing price at least USD 5; ADV20 and ADV63 each at least USD
  2,000,000; 252 completed sessions; price above SMA50; SMA50 above SMA200;
  and SMA200 higher than its value 20 sessions ago.
- Persistence: at least 24 of the latest 32 completed closes must have been
  above the then-available SMA200. Extension above SMA50 must not exceed 8%.
- Ranking: highest 32-session trend-persistence count, with lower annualised
  63-session realised volatility as the tie-breaker. No return-lookback score
  is used.
- Portfolio: 12 equally weighted positions. Month-end signal, next-open entry
  and next-open rebalance exit.
- Risk: SPY above its SMA200 is risk on; otherwise 100% cash. A held stock
  exits at the next open after its close falls below its then-available SMA50.
  There is no fixed percentage stop.
- Costs: existing round-trip cost and slippage assumptions are retained.
- Test: 2023-02-01 onward with point-in-time data and no look-ahead. OOS
  begins 2025-03-31. Massive Starter's five-year entitlement is respected.

## Decision rule

GO requires all of the following for both the full test and OOS segment:

1. Positive net return.
2. Return above SPY.
3. Daily maximum drawdown no worse than 20%.
4. Monthly-period hit rate at least 50%.
5. OOS has at least 12 complete monthly periods.

A failed gate is recorded as NO-GO, with the output artifacts retained for
inspection. The app, Buy Now, production model, fictitious portfolio and all
orders remain unchanged unless every gate passes.

Current limitation: survivorship bias
