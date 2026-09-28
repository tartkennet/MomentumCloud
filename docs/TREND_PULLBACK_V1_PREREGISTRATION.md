# Trend-pullback v1 — pre-registration

This is one replacement candidate for PR 13. It is intentionally different from the rejected 12–1/6–1/3–1, breakout, relative-strength and beta-adjusted candidates. It is not an app or production model.

## Objective

Own established long-term trends after a controlled pullback, rather than chase the strongest trailing returns.

## Universe and timing

- Point-in-time US-listed common stocks only. Exclude ETFs, ADRs, warrants and preferred shares.
- Close at least USD 5, ADV20 at least USD 2,000,000 and at least 252 trading sessions.
- Signal at month end. Entry, stop and rebalance exits execute at the next available opening.

## Stock selection

- Close above SMA200.
- SMA50 above SMA200.
- SMA200 higher than its level 20 sessions earlier.
- Close is from 0% to 10% above SMA50. Names below SMA50 or more than 10% extended above it are excluded.
- Rank eligible names by the percentage spread of SMA50 above SMA200, reduced by the percentage extension above SMA50. This favours the strongest established trends that have pulled back close to support.
- No 12–1, 6–1, 3–1, breakout, relative-strength or beta-adjusted return score is used.

## Portfolio and risk

- 15 equal-weighted positions, monthly rebalance.
- SPY above SMA200 is risk on; otherwise 100% cash.
- Fixed 10% stop-loss only.
- Same point-in-time data treatment, costs and slippage as PR 13.

## Validation

- Start: 2023-02-01. Untouched OOS begins: 2025-03-31.
- GO requires positive net return, better than SPY, daily maximum drawdown no worse than -20%, at least 50% winning periods, and at least 12 OOS periods in both total and OOS assessment.
- No parameter changes after the run. A failed run is NO-GO.

Current limitation: survivorship bias
