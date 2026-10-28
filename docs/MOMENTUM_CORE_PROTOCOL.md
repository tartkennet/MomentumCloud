# Momentum Core v1 — frozen candidate, 2026-10-26

This is a new candidate, not a repaired or re-labelled v4-balanced approval.
The rules below were written before running this candidate's performance.
The already inspected 2023–2026 history is development data. A historical
pass is not independent evidence and cannot authorize live purchases.

## One selection rule

US common stocks (CS), active on the signal date, listed on XNAS/XNYS/XASE;
exclude acquisition/blank-check/SPAC names using the name on that date.
Use the historical reference endpoint, never today's workbook constituents.
Require 253 consecutive trading-session closes, nominal price >= USD 10,
and mean actual traded dollar volume over 20 sessions >= USD 5 million.
Rank only by split-adjusted 12–2 price momentum: close[t-21]/close[t-252]-1,
descending, ticker as deterministic tie-break. Require positive momentum.
Select at most 15. No 6–2 factor, weighted score blend, extension filter,
individual moving-average filters, or fixed 10% individual stop.

## Risk and timing

Daily SPY close strictly above its 200-session split-adjusted moving average
permits stock exposure. Otherwise target cash. At the first completed close
of each calendar month, or on a daily risk-off to risk-on transition, rank
again. Execute targets at the following session's observed raw open. Never
use the signal close as a fill or the execution open to select replacements.
Weight the selected stocks by inverse volatility of the last 63 daily returns,
with a 10% target cap per stock. Unallocatable weights remain cash. No leverage,
shorts or individual loss-cap claim. The cap applies at target formation;
weights can drift between rebalances. Fewer than 15 eligible names means cash
for the missing sleeves, not a weaker eligibility rule.

Use one daily cash/share/receivable ledger in replay and paper operation.
Target dollar budgets use signal-close NAV, not next-open NAV. Sell first,
then buy whole shares proportionally within actual available cash, allowing
for fees and gaps. Unchanged shares incur no cost. Base one-way cost is 15 bps
of actual traded notional (the old 30 bps round trip). Also replay at 30 bps
one way, without changing selection parameters. Zero interest on cash. USD
accounting, no tax or SEK FX claim; starting equity USD 100,000.

## Data and accounting

Fetch unadjusted OHLCV (adjusted=false). Adjust historical signal closes only
for splits effective on or before that signal date. Apply splits to actual
shares at the start of the execution date. Future splits cannot rewrite the
nominal USD 10 threshold. Raw prices also define fills and dollar liquidity.
Dividend cash_amount, not today's split_adjusted_cash_amount, belongs to
pre-ex-date holdings; accrue at ex-date and make it spendable only on pay date.
Missing currency/payment facts for a held dividend block the run. Benchmark
SPY receives the same dividend and split accounting, starts at the first
execution open, and pays the same purchase cost. No artificial terminal sale.

Previously verified cash mergers become cash receivables at their effective
date; absent a verified pay date the claim is valued but never reinvested.
Verified stock exchanges convert shares; fractional consideration remains a
valued, non-tradable fraction (no invented cash-in-lieu fill). Unknown missing
prices for held securities block the run. A missing buy open cancels that
order and leaves cash; it does not cause a hindsight replacement. Missing sell
opens block the run. Ticker changes do not splice unverified signal histories. Documented 1:1
renames preserve the same issuer's pre-change bars and applicable split
history, only once the change is effective. Reused symbols from another
issuer and stock-merger target/acquirer histories are never joined.
Non-tradable contingent merger rights are recorded separately at zero carrying
value, with their contractual maximum disclosed; they are not guaranteed cash.
An old merger/ticker conversion cannot cancel or rename a new issuer's order
formed after that event. Corporate-action cancellation applies across the
signal-to-execution interval, not indefinitely to a symbol that can be reused.

## Evidence and approval

Write separate Momentum_core_* artifacts, including data errors, all trades,
daily equity, decisions, targets and model/source hashes. Never overwrite the
v4 validation decision or feed Core paper orders into v4 Buy Now/dashboard.
Replay uses the same decision/ledger functions as incremental paper replay.
Source hashes invalidate changed paper checkpoints. The forward paper record
also rejects any revision to previously recorded daily NAV, trades or targets.
Daily paper resumes the saved base/stress strategy and benchmark ledgers,
loading only new sessions plus the rolling signal warmup; it does not depend
on re-downloading the entire paper history as the API's two-year window moves.
The full checkpoint is included in each artifact and recovered if the cache is
evicted. A missing original checkpoint after 2026-10-30 12:00 UTC blocks the
record: retrospective reconstruction cannot masquerade as forward evidence.
It starts only after the frozen code is published; historical replay is labelled
DEVELOPMENT. Historical gates retain the five existing economic thresholds:
at least 30 complete monthly periods, positive net return, positive total edge
versus SPY, daily drawdown no worse than -20%, monthly hit rate >= 50%.
Each gate must show its measured value. Data failures are DATA_BLOCKED,
never a synthetic zero-return PASS. A historical pass alone is PAPER_ONLY;
live_approved is false. No broker order submission exists in this candidate.

## Data documentation

- https://massive.com/docs/rest/stocks/aggregates/daily-market-summary
- https://massive.com/docs/rest/stocks/corporate-actions/splits
- https://massive.com/docs/rest/stocks/corporate-actions/dividends
- https://massive.com/knowledge-base/article/does-massive-adjust-historic-dividends-for-splits

The cost assumption, market-close risk gate, open fills, and gross-of-tax
dividends are explicit modelling limitations, not guaranteed execution or
capital protection. Performance is not used to retune the frozen candidate.

## Reproducibility with one paid data period

The observed session calendar, raw prices, dated instrument records, splits
and dividends are preserved with the source revision and input hashes.
`--offline` makes no API calls and blocks on any missing input rather than
silently fetching or replacing it. The workflow exports the research inputs
encrypted to a private recipient; no raw input archive is published in the
public evidence artifact. This changes input preservation, not the strategy.
Actions raw-input caches are authenticated and encrypted with the existing
credential before upload; superseded unencrypted Core caches are removed after
a successful export. The separate recipient-encrypted archive supports offline
research even after an API credential is rotated.

## Forward cohort v2 (operational restart, 2026-10-28)

The original 2026-10-27 cohort never acquired its first checkpoint: the
2026-10-28 scheduled job started at 13:18 UTC, after its 12:00 UTC bootstrap
deadline. That failed record is preserved; it is not reconstructed as paper.
The corrected source is frozen before a new first signal on 2026-10-29.
Its original checkpoint must be recorded by 2026-10-30 12:00 UTC. A separate
v2 cache and artifact prevent adoption of the failed cohort's identity.
Four scheduled attempts (00:20, 03:20, 06:20 and 09:20 UTC, Tuesday–Saturday)
reduce dependence on one delayed GitHub schedule. A late first record still
blocks; no retrospective or fabricated forward history is permitted.
Historical replay dates, model parameters and economic gates are unchanged.
