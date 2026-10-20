# Broad Momentum Selection v3

Fixed before computing this comparison's returns, 20 October 2026, following the user's instruction to rebuild an overly strict selection.

The experiment changes stock selection only. Risk Managed Momentum v2's sizing, position count, 5% initial cap, unlevered 15% covariance risk target, monthly entry schedule, daily SPY exit, no intramonth reentry, 10% close-detected stock stop, actual next-open fills and fixed monthly cost remain unchanged.

## Broad eligible set

Use the same historically dated US common-stock universe. Require 253 consecutive finite positive adjusted closes, actual raw signal price at least USD 5, and actual raw ADV20 at least USD 2 million from all twenty sessions. Estimated 63/126-session volatility must be finite and positive so that unchanged risk sizing is defined. Missing source observations cannot be invented. These are tradeability and data requirements, not outcome-based exclusions.

Remove ALL other v2 selection gates: positive momentum at each horizon, price above SMA200, rising SMA200, maximum 60% volatility, maximum 25% recent daily move, and maximum 25% extension above SMA50. Negative momentum stocks remain eligible for relative ranking; the separate SPY portfolio regime is unchanged. No stock or sector blacklist is added.

## Two declared selectors, no search

1. **Broad ordinary momentum**: cross-sectional percentile ranks of completed 12–1, 6–1 and 3–1 price returns, combined 50/30/20. The 21 most recent sessions do not enter those completed momentum numerators. Sort descending score, then ascending ticker.
2. **Broad risk-adjusted momentum**: the exact same eligible set and rank combination, but divide each momentum by current 126-session volatility before percentile ranking. Risk affects relative preference rather than excluding names at a fixed cutoff.

Select up to 25 from either ranking on each risk-on monthly signal. Do not apply a further individual momentum sign or price-trend test. Missing slots remain cash; no lower-ranked replacement is chosen based on later execution or returns.

Recompute the strict v2 baseline in the same process using its unchanged selector and the exact same risk/execution functions. Its net return, drawdown and monthly results must reproduce the archived v2 before new results are accepted. All original outputs stay intact.

## Evaluation and limits

Use the same 43 signals and frozen price basis. Compare net and gross return, daily drawdown, cost stress, average exposure, selection breadth, overlap and turnover of choices. Add SPY price buy-and-hold with the same fixed cost and separate SPY controls matched to each selector's initial exposure and daily market gate. Matching initial exposure does not match every stock stop or prove alpha.

The earlier goals, positive net return and drawdown no worse than 20%, are unchanged. The historical periods have already been used for design and inspection; no result is labeled fresh out-of-sample, no thresholds are subsequently fit to turn a row positive, and no historical winner is automatically activated for buying. Good arithmetic does not establish that every grouped price or historical identity has an individual reference check. Preserve all incomplete evidence and block complete returns when a selected trade lacks an executable/valued path.

## Execution clarification before the first aggregate return

The expanded set contains pending cash acquisitions that cease trading before the intended entry. When an exchange/issuer document confirms that the order cannot fill, preserve that name in the selected list, record the canceled zero-fill order and retain its entire intended allocation as cash. Never invent an opening price, buy a replacement, or redistribute its weight. An arbitrary missing quote without such evidence remains blocking. This is an order-execution clarification, not a new return or ranking parameter; it does not affect any archived strict-v2 order. The full-month cost remains payable when other positions are invested.

If a secondary selector has a genuinely unresolved observation, retain all its choices and block its performance independently. Such a gap must not prevent a fully observed primary broad-momentum variant or the strict baseline from completing. Do not publish a whole-sample return with a missing lot silently omitted.

Where BOTH individually requested raw and adjusted daily series omit a held stock's close, estimate its daily NAV at the last actually reported close on or after entry, recording that price's original date on every use. Do not represent it as a fresh close, a verified no-trade day or an executable fill. The last quote cannot generate a newly observed stop signal. Exact observed opening executions remain mandatory. This pre-aggregate clarification is a disclosed stale-quote convention and makes affected comparisons provisional rather than fully observed-price validated. An unconfirmed missing close, incompatible basis, missing prior mark or unavailable execution remains blocking. Apply identically to all selectors; preserve strict-v2 parity and all source responses. No stock is removed or replaced because of a later gap.
