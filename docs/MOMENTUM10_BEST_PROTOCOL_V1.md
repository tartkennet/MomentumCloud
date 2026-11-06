# Momentum 10 BEST v1 — prospective preregistration

Frozen before the first BEST data run, 2026-11-06. BEST is an experiment name,
not a claim that the portfolio will outperform. No parameter search, fitted
return target, historical economic GO, or real-money approval.

## Scope and clock

Examine every dated US common-stock record supported by the existing complete
PIT reference snapshot, XNAS/XNYS/XASE, active on the signal date, unique CIK.
No ETF, SPY, preferred, SPAC or cash shell. No ADV100 truncation. Raw price >=
USD10, ADV20 >= USD20m, 253 consecutive observed sessions including positive
close/volume on the latest 20 sessions. Missing history is disclosed per name;
missing universe/calendar/benchmark blocks the formation. Sector metadata must
be dated provider reference data, not guessed from names. Reference metadata
missing for a high-ranking name blocks formation rather than silently dropping
it. Historical replay must never apply today's constituents or classifications.

Use split-adjusted closes, including only events effective by the signal day.
Price-only momentum excludes dividend reinvestment; dividends, native currency,
mergers and splits are accounted for by the prospective ledger. All dates and
source hashes are retained. Only already-observed completed closes form signals.
No revised/future fundamentals are used in ranking.

## Score fixed ex ante

Newest close is C[0]. Returns: M12_1=C[21]/C[252]-1; M6_1=C[21]/C[126]-1;
RS12_1 and RS6_1 divide those gross returns by the identical SPY intervals.
Vol63 is sample standard deviation of the latest 63 simple daily returns times
sqrt(252). Risk-adjusted momentum is M6_1/Vol63. Persistence is the fraction of
63 sessions whose close exceeds its trailing 50-session simple mean.

Across all complete liquid common stocks, compute midrank percentiles (ties
share their rank). Score = 35% percentile(RS12_1) + 25% percentile(RS6_1) +
25% percentile(M6_1/Vol63) + 15% percentile(persistence). Descending score,
then descending RS6_1, then ticker are the deterministic tie breaks. No
fundamental score or capital enters membership.

Strong eligibility requires positive M12_1 and M6_1, positive RS6_1, positive
63-session return, current close > SMA50 > SMA200, and positive volatility.
The formation pool is the first 40 ranked strong names only. Lower-ranked or
weak names are never inserted to force ten. Every skip and its original rank
is published. If the feasible pool has fewer than ten, report insufficient
strong breadth and remain in cash (or commit an observed exit for prior holdings).

## Diversification and capital

Select greedily in frozen score order, one issuer, at most three names per
2-digit SIC industry and six per SIC division. Positive daily-return Pearson
correlation >=0.85 over the same 63 sessions connects names into risk clusters
(connected components of the strongest 40); at most four names per cluster.
Industry, division and cluster choices are transparent, not a claim of pure
unconstrained top-ten rank. No hidden fallback or cap relaxation.

After membership, derive the minimum whole-share capital: one share each plus
2% limit buffer, max(USD1, 25bp commission), 25bp FX and 15bp execution reserve.
Reserve-based capital caps: issuer20%, industry35%, SIC division60%, correlation
cluster50%. Round every reserve upwards to cents. Minimum capital is the maximum
of total reserves and each group's reserve divided by its cap. No fixed SEK
amount or investment cap. An explicit owner amount may be used before cohort
initialization; default AUTO_MINIMUM locks the independently audited minimum.
The browser's capital/cash choices do not alter membership or the locked account.

Allocate new positions toward capped inverse Vol63 weights, always reserve one
whole share first. Retain unchanged quantities of selected qualifying holdings;
sell departing members before conditional new buys. Existing positions violating
caps block new buying; no fictitious fractional resizing. Do not borrow.
Publish base and doubled-friction cost scenarios; neither is a fitted backtest.

## Prospective controller and safety

Separate BEST state, decisions, fills, marks, source receipts and hash-chained
publication. No reuse of prior account transactions, capital or initialization.
Monthly formation locks a valid ten-name basket. Daily SPY close>SMA200 is RISK
ON, otherwise target cash. RISK OFF cancels buys before execution. Missing or
unverified data pauses buying and preserves honest dated holdings; it is not
silently interpreted as a valid risk exit. Insufficient strong breadth with
verified inputs targets cash and is disclosed.

Commit exact quantities before a future opening. Only raw positive-volume
opening quotes actually observed in 09:30–11:30 America/New_York can execute,
with the existing 2% buy limit, actual cleared cash, sells first and independent
ledger reconciliation. Missed openings are recorded, never backfilled. Partial
baskets are explicitly blocked for review. Paper fills are modeled, not broker
or realtime confirmations. A paper start requires actual recorded opening fills.
Cash initialization and plans are not completed purchases.

Daily NAV uses observed raw closes, dated ECB FX and reconciled events/costs.
Newly filled positions awaiting a close have no invented NAV. SPY is benchmark
only in a separate account. Old frozen Avanza/H3/Quality accounts and histories
remain untouched; compare only genuinely overlapping observed dates. No
survivorship-biased current-universe historical performance is presented.

PAPER_EXPERIMENT may run when technical, data, and financing audits pass,
regardless of historical economic NO_GO. Economic and real-money GO remain
blocked; existing legacy economic gates are unchanged. No broker integration.

## Validation and deviations

Tests must cover future/split mechanics, full-universe scope, independently
recomputed scores and correlations, exactly ten/cash fallback, identical names
across capital, minimum whole lots/caps/costs, observed timing, no backfill,
retention, RISK OFF, partial fills and independent cash/positions/NAV audit.
Protocol changes require a new version/cohort and an explicit deviation entry;
never optimize parameters after inspecting BEST outcomes. Implementation bug
fixes must be documented without changing the frozen numerical rules.
