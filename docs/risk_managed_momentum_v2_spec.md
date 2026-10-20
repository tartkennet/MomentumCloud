# Risk Managed Momentum v2

Specification fixed before computing any v2 historical returns, 20 October 2026.
This is one research design, not a parameter search or production approval.

## Selection

- The existing historically dated US common-stock universe and instrument/name filter.
- At least 253 consecutive valid adjusted daily closes. No current-membership list.
- Actual unadjusted signal close at least USD 10; actual raw dollar turnover averaged over all 20 most recent sessions at least USD 20 million. Missing observations cannot be treated as zero or inferred from adjusted volume.
- Price above a rising SMA200, with positive completed 12–1, 6–1 and 3–1 momentum.
- Annualized close-return volatility over both 63 and 126 sessions at most 60%; any absolute daily close return above 25% during the latest 63 sessions disqualifies the stock at that signal only.
- Price at most 25% above SMA50. These coarse limits address liquidity, recent instability and stretched entries; they do not identify the old losing tickers by name or industry.
- Cross-sectional percentile ranks of each completed momentum divided by current 126-session annualized volatility, combined 50/30/20. Ties resolve by ticker. Up to 25 names; vacant allocations stay cash.

## Risk and execution

- Normalize inverse-63-session-volatility weights, cap each at 5% of initial monthly NAV, then scale the entire basket down to a 15% ex ante annualized volatility target using the full 63-session sample covariance. No leverage. Missing slots retain at least their 1/25 cash allocation. The 5% limit applies at rebalance; price appreciation can increase a holding's later weight.
- Enter at the next session's actual open after a month-end signal if SPY closes above SMA200. Do not silently substitute a later entry or lower-ranked name when data are absent.
- Retain the 10% stock stop observed at the close, executed at the next actual open. Never assume the threshold is a guaranteed fill.
- Check SPY against SMA200 at every close. A failed gate liquidates at the next session's actual open. Remain in cash until the next monthly rebalance; no discretionary intramonth reentry.
- After any exit the proceeds stay cash until the next rebalance. Corporate actions use the existing evidence-backed price-basis converter. An unresolved exit or valuation blocks the result, rather than removing the position.
- All signals use only history dated on or before the signal close. Covariance and weights never inspect the holding month's returns.

## Fixed evaluation

Use the same 43 month-end signals, entry/exit calendar and frozen October 6 price basis as the rejected robust v1 monthly replay. Preserve all original outputs.

Evaluate exactly three declared variants: (1) new selection with equal 1/25 weights and the old monthly SPY gate; (2) the same choices with the new weights and the old monthly SPY gate; (3) the full v2 design including daily SPY liquidation. These are component diagnostics, not a contest whose best historical row becomes production.

Charge the same fixed 0.30 percentage point cost in every month with a nonzero initial stock allocation. Cash earns zero. Also report 0.60 percentage point cost stress without changing trades. Compare with the old robust v1, SPY price buy-and-hold with the same fixed monthly cost, and SPY matched to v2 initial exposure and daily gate. Dividends, tax, SEK/USD changes and actual brokerage fills are outside this price-return research test.

Primary research goals: positive net return and daily drawdown no worse than 20%. Separately disclose whether total return and return/drawdown improve on SPY; lower risk alone is not evidence of stock-selection alpha. All 43 periods have already been inspected during earlier work and cannot be relabeled unseen out-of-sample data. Report annual/subperiod outcomes and missing evidence explicitly.

The design uses the general principles of risk-adjusted momentum and volatility management. It does not reproduce an MSCI index or the Moreira–Muir paper. Thresholds, target risk and caps above are design choices, not empirically proven optima.

References: https://www.msci.com/indexes/group/momentum-indexes ; https://www.nber.org/papers/w22208 .
