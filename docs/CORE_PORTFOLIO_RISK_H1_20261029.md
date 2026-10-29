# H1: benchmark-referenced aggregate risk budget

This hypothesis is frozen AFTER read-only diagnosis of completed PR23 and BEFORE any new candidate performance. Diagnosis source: 2268b9b; Actions 40858434977; verified evidence ZIP SHA256 c12d7cd081badd809cdaea79168967344cb7a8c8f9fda53b728faa92f63a83d7. All 709 daily P&Ls reconcile independently (max error 6.37e-11 USD). Original raw input hashes are unchanged.

## Evidence, not a retrospective exclusion list

The three largest non-overlapping peak-to-trough losses are 2026-06-22–2026-10-16 (−36.262%, SPY +2.719%), 2024-11-11–2025-05-13 (−32.427%, SPY −1.366%) and 2025-10-15–2025-12-17 (−24.469%, SPY +0.919%). The first and third have exclusively SPY risk-on signals. The largest episode retains at least 12.4 effective stocks and no single observed weight above 12.3%; it is not chiefly one oversized holding. WDC, VICR, ANRO, STX, BW, SNDK and BE contribute substantial losses across multiple industries.

The existing inverse-volatility weights normalize away the LEVEL of aggregate risk. Across the 37 fixed signals estimated stock-basket risk is 1.135–4.561 times SPY (median 2.891). At 2026-07-01 it is 62.4% annualized versus SPY 13.7%, weighted pair correlation .378 and SOXX correlation .832. At August's signal SOXX correlation is .861. The historical universe has no SIC/sector field; ETF correlations are proxy evidence, not invented historical sector labels. No named-stock or sector exclusion is introduced.

## One change, with no calibrated target or new window

At each EXISTING monthly/re-entry stock signal, keep exactly the audited PR23 rank, eligible count, securities and capped inverse-volatility weights w. Using the latest existing 63 split-adjusted daily simple returns including the completed signal close, calculate the return series of that FIXED target basket, r_p[t] = sum_i w_i r_i[t]. Calculate sample standard deviations sigma_p and sigma_SPY from the same dates. Multiply EVERY original stock target weight by a = min(1, sigma_SPY / sigma_p). Unallocated capital remains cash, earns zero, and is never borrowed. If required observations or variances are invalid, block rather than invent a risk estimate.

The target is relative to the existing benchmark, not a fitted 10%, 15% or 20% annual volatility. Risk horizon, ranking, stock sizing proportions, timing, corporate actions, 15/30bp costs and SPY/SMA200 risk-off behavior remain unchanged. No daily churn rule, drawdown stop, new trend indicator or threshold search. The estimate uses split-adjusted price returns, consistent with existing sizing; dividends remain in the independently audited realized account. Risk is an estimate, not a guaranteed drawdown limit.

Falsifiable prediction: this controls the excessive basket risk and reduces the common-stock drawdowns. It may also reduce return through cash drag; beating SPY is still mandatory. Do not relax that gate if it fails. Aggregate volatility management has independent research precedent (Moreira and Muir, Volatility-Managed Portfolios, Journal of Finance 2017; https://www.nber.org/papers/w22208); that paper does not validate this exact implementation or its future return.

## Complete fixed evaluation

Run all 40 existing marking/payment/cost/phase accounts, preserving every failure. Reuse hash-verified completed PR23, PR22 and Core controls without refetching prices or repeating old strategy studies. Compare return, daily drawdown, zero-RF Sharpe, actual fees, calendar years and the separately resumed September–October period. Independent selection validation checks unchanged base ranks, ex-ante variance by a different algebra, weights, signal dates and next-observed-session fills. The separate accountant reconstructs shares, cash, actions, trades, costs, NAV, SPY and financial metrics. No gate changes, no future data, no certified untouched holdout claim.

All historical all-gate passes are PAPER_ONLY. Production/Buy Now, frozen original Core identity and live permissions remain unchanged. If H1 fails, retain it and diagnose the actual failure before considering one separately justified hypothesis; do not tune its risk level.
