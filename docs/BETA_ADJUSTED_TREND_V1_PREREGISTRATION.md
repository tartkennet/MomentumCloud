# Beta-adjusted trend v1: pre-registration

Status: one-shot validation candidate after robust-momentum-v1 was NO-GO.

This candidate is a separate model family. It does not use the failed 12-1/6-1/3-1 rank blend, breakout thresholds, or any prohibited legacy model.

## Fixed rules before the run

- Universe: point-in-time US-listed common stocks only. ETFs, ADRs, warrants and preferred shares are excluded by the security master.
- Eligibility: closing price at least USD 5, ADV20 at least USD 2,000,000, 253 completed sessions, and price above SMA200.
- Signal: completed 12-2 month stock return minus realised beta times completed 12-2 month SPY return. Beta is covariance of stock and SPY daily returns divided by SPY return variance over the same completed formation window. Only positive signals qualify.
- Ranking: descending beta-adjusted 12-2 signal. No 6-month or 3-month signal is used.
- Portfolio: 15 equally weighted names, monthly month-end signal and next-open execution.
- Risk: SPY above SMA200 is risk on; otherwise 100% cash. Fixed 10% stop, executed at next executable open.
- Costs: unchanged existing round-trip cost and slippage assumptions.
- Test: 2023-02-01 onward, point-in-time data, no look-ahead. OOS begins 2025-03-31.

## Decision rule

GO requires both total period and OOS to have positive net return, beat SPY, maximum daily drawdown no worse than -20%, period hit rate at least 50%, and at least 12 OOS periods. Otherwise it is NO-GO and is not tuned.

No production model, Buy Now, app, fictitious portfolio, broker order or automated trading process may change from this candidate alone.

Current limitation: survivorship bias
