# Trend-following persistence v1: pre-registration

Status: one-shot candidate following the verified NO-GO of PR 13's seasoned durable liquidity trend. This is a different model family: it does not rank 12-1, 6-1 or 3-1 returns, does not use beta-adjusted returns, and does not use a fixed percentage stop.

## Fixed rules before the run

- Universe: point-in-time US-listed common stocks only. ETFs, ADRs, warrants and preferred shares are excluded by the security master.
- Eligibility: closing price at least USD 5; ADV20 and ADV63 each at least USD 2,000,000; 504 completed sessions; price above SMA50; SMA50 above SMA200; and SMA200 higher than its value 20 sessions ago.
- Persistence: at least 50 of the latest 63 completed closes must have been above the then-available SMA200. Extension above SMA50 must not exceed 8%.
- Ranking: highest 63-session trend-persistence count, with lower annualised 63-session realised volatility as the tie-breaker. No return-lookback score is used.
- Portfolio: 12 equally weighted positions. Month-end signal, next-open entry and next-open rebalance exit.
- Risk: SPY above its SMA200 is risk on; otherwise 100% cash. A held stock exits at the next open after its close falls below its then-available SMA50. There is no fixed percentage stop.
- Costs: existing round-trip cost and slippage assumptions are retained.
- Test: 2023-02-01 onward with point-in-time data and no look-ahead. OOS begins 2025-03-31. Massive Starter's five-year entitlement is respected.

## Decision rule

GO requires both total period and OOS to have positive net return, beat SPY, daily maximum drawdown no worse than -20%, period hit rate at least 50%, and at least 12 OOS periods. Otherwise the candidate is NO-GO and is not tuned.

No production model, Buy Now output, app, fictitious portfolio, broker order or automated trading process may change from this candidate alone.

Current limitation: survivorship bias
