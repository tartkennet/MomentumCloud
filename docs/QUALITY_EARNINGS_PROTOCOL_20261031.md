# Quality & Earnings v1 — frozen economic hypothesis before outcomes

Issue #35, PR #36. ONE new business-based hypothesis, no parameter matrix.
Prior v1–v3 rankings are not reused. Their results and frozen H3 are unchanged.

Evidence motivates underreaction to earnings news and business profitability
(NBER w5375/w15940), not the success of this ten-stock implementation. We test
whether genuinely improving profitable, cash-generative businesses with
market-relative price confirmation are more durable than extreme price winners.
Reported EPS growth is NOT earnings surprise or analyst-estimate revision.
Verified point-in-time estimates/revisions are unavailable and excluded.

## Data and universe

Use actual original SEC XBRL filing instances delivered through the existing
provider's filing-file entitlement (verified on the app's own key). This is
separate from its unentitled/restated Financials API. Preserve bytes, SHA256,
accession, CIK, period bounds, unit, concept, filing/acceptance metadata and
actual observation time. SHA changes for an existing accession are quarantined.
Never backdate a newly collected snapshot. Prospective decisions require
observed_at <= actual decision timestamp and source observed within24hours.
Require latest 10-Q/10-K from both form streams, no future filing, latest filing
<=140days old, amended or conflicting facts require review. Fiscal YTD in10-Q
compares with fiscal YTD one year earlier; 10-K compares full years. Never mix
quarter/YTD/annual or infer missing custom tags as zero. All four facts below
must share an unambiguous whole-entity USD period and comparable prior period
in the SAME original filing. EPS uses USD/share; current-file comparatives
share that filing's split basis. Missing/unsupported data are explicit gaps.

Current collection is NOT a certified historical panel. Original-file retrieval
is working, but no complete vintage/coverage and sector-identity panel for all
past/delisted liquidity universes has been audited. Do not backtest today's
100 companies or current figures across prior prices. Historical new-model
return/DD/Sharpe stay null until that independent data audit exists. Existing
reviewed price history is not untouched validation. This delivery prioritizes
honest prospective source capture instead of spurious historical performance.

At each signal use dated US primary XNAS/XNYS common-stock records, exclude
acquisition/SPAC names, complete253 split-adjusted closes, raw close >=USD10,
ADV20 >=USD20m. Price confirmation: 126-session price ratio strictly exceeds
SPY's same ratio and current close>SMA200. Price strength is eligibility ONLY;
extreme past gain receives no ranking bonus. Exclude a minimum single share
above20% of current NAV. Of this observable liquid confirmed set, consider the
100 highest ADV20 (ticker breaks ties). This capacity universe is fixed before
results, not handpicked names. Save full membership/exclusions each observation.
One issuer/CIK at most. SEC SIC observed from the current original-filing
metadata must be known; financials60–69, utilities49, public90–99 and unknown
industries excluded because this cash/net-margin comparison is unsuitable.
Current SIC is never assigned retrospectively. Track historical classifications
separately before any historical sector-cap claim.

## Business eligibility and ranking

Same-period original US-GAAP concepts: revenue (priority customer revenue,
Revenues, SalesRevenueNet), NetIncomeLoss,
EarningsPerShareDiluted, NetCashProvidedByUsedInOperatingActivities.
Require revenue growth>0; prior diluted EPS>0 and current EPS>prior; positive
current net income with non-decreasing net margin; positive net
income both periods; positive operating cash flow both periods, current CFO
>=current net income. This is cash backing of earnings, not a valuation model.

Rank by equal mean of three cross-sectional midrank percentiles: revenue
YoY growth, diluted EPS YoY growth, net-margin change. Ticker tie break.
No weighting/horizon/threshold search or ticker exclusions after outcomes.
Greedily take10: max2 names per SIC two-digit industry and max4 per SIC broad
division, oneCIK, funded whole minimum lots. Minimum risk/cash feasibility is
checked; insufficient complete baskets remain BLOCKED, not nine-stock success.
Target equal money with integer minimum1; additional lots go to the least
funded new name while cash/risk permits. Ex-ante max20% per name,30% per SIC
industry and50% per broad division at the conservative limit prices. These are
planning limits, not a guarantee against gaps or later weight drift.

## Decisions and practical fills

SEK20,000 prior-date ECB reference into USD accounting; SEK benchmark uses
exact same dated currency. Reuse verified event/cash/claim and fee infrastructure.
No borrowing, ETFs or SPY holdings; SPY is a separate comparison account only.
Order cost max(USD1,.25% notional)+.25% FX reserve+15bp execution reserve;
30bp reserve is the documented stress, not measured live spread. Account is
before tax, consistent with existing gates. Actual retail broker availability
for individual symbols and realized spreads cannot be certified from market
listing alone; display that limitation before any live approval.

Monthly re-selection: first genuinely observed pre-open/after-close decision
for a new month. Retain quantities in the qualifying constrained top10; no
routine top-ups or sell/buy round trips. Daily SPY close<=SMA200 commits exits
to cash. No individual stop in this first fundamental hypothesis; unsupported
business thesis exits at next monthly selection, not retrospectively. Failed
new quality data suspend new purchases; never invent fundamentals to trade.

Commit exact integer quantities, source hashes, time and buy-limit102% of known
last close BEFORE any eligible opening. Sell excluded names first; plan buys
against cash plus conservative98%-of-close sale proceeds. At actual fill time
use ONLY actual cash/proceeds; underfunded/unfilled orders stay cash, never
borrow, resize using future prices, or invent replacements. Buy only if the
observed next opening <= committed limit. An opening gap can leave a partial
cash basket; expose this, never claim ten full positions. No same-day after-
opening signal can fill at that opening. Record quote-observed and modelled
execution timestamps separately. Execution prices are paper assumptions, not
broker fills. Missed opening observation windows are skipped, never backfilled.
Global RISK OFF is independent of the monthly clock; re-entry can commit a new
basket with the latest qualified data. Ordinary failures do not quietly loosen
industry/budget rules. No automatic retries of failed economic alternatives.

## Prospective start and validation

A paper-start permit requires frozen code/parameters; >=90% resolved data
coverage of the whole predefined capacity universe; exactly10 funded targets;
all selected primary facts and timestamps independently checked; current dated
FX/prices; no missing sector/issuer identities; all accounting/order checks PASS.
An opening execution capability must be observed in the actual allowed window
before any simulated trade is booked. Prior-session price availability alone
is not proof. Before that, state is PAPER_READY_AWAITING_SESSION, no fake trades.
If criteria fail: DATA_BLOCKED or SELECTION_BLOCKED, collection continues.
No live or broker order capability is introduced.

Paper admission is not historical financial GO. The five existing USD gates
remain: >=30 complete monthly intervals, positive net return, edge>SPY,
DD>=-20%, positive-month rate>=50%. Future assessment additionally requires
source continuity, complete audited observations and realistic liquidity/cost
checks. Missing historical or true prospective evidence never permits live-GO.
Economic status stays NO_GO_INSUFFICIENT_EVIDENCE while unassessed. Every failed
or missing criterion is visible. No new economic variant until this hypothesis
has evidence; historical approval does not authorize actual money.

## Registered data-feasibility alternative, before any financial outcome

The original operating-margin extraction prototype (commit0739238, run41210207368)
resolved83/100 issuers, below the predeclared90% source minimum. Eleven lacked
a standard operating-income fact; they were NOT imputed as zero or pretax
income. No strategy return, backtest or real prospective trade was computed.
Preserve that failed data audit in QUALITY_EARNINGS_FIRST_DATA_AUDIT_20261031.json.
Register ONE explicit alternative: original-file NET profit margin (NetIncomeLoss
/revenue), with the same earnings/cash/revenue constraints, percentile ranking,
universe, fees, sector/whole-lot rules and90% coverage minimum. Net margin is
a distinct profitability measure and may include non-operating/tax effects;
CFO>=net income remains a cash-quality check, not proof that profits recur.
This change addresses documented reporting coverage, not a favourable return.
Model identity is momentum10-quality-earnings-net-v1. There are no other field,
threshold or horizon alternatives in this register. Any subsequent prototype
return would be a separately registered study, never quietly merged into v1.


## Operational paper freeze, before the first possible market opening

Prospective accounting uses a non-borrowed USD cash subaccount. SEK20,000 is
anchored to the strictly prior-date ECB USD/SEK fixing; the cash thereafter has
USD currency exposure, as do the stocks and the benchmark. The per-order25bp
FX charge is a conservative conversion reserve, not a claim of the exact cash
sweep mechanics of a standard SEK ISK. Actual broker/account support and
instrument availability remain unverified prerequisites for any live approval.
This listing universe includes US-listed foreign issuers (for example SHOP);
NYSE/Nasdaq listing is not a claim of US incorporation. No fund holdings.

The controller freezes hashes of the economic code, parser, protocol and reused
bookkeeping dependencies. A changed fingerprint blocks continuation of that
cohort. Serialize scheduled runs; the independent ledger verifier checks raw
observed opening quotes, committed quantities, costs, splits, native dividend
claims/payments, mergers/distributions and NAV. Append full accepted state and
previous-state SHA to unique journal paths; never overwrite prior decisions,
trades or equity observations. Archive original receipts separately in draft
releases, authenticate input files, keep two encrypted rolling market caches,
and publish the durable pointer only after successful preservation. Ordinary
fast-forward Git pushes reject concurrent writers. Public journals contain no
API keys. Repository administrators can alter Git history; hashes and separate
immutable observation releases make changes detectable, not cryptographically
impossible. No broker clients or order API credentials are used.

Production schedules Mon–Fri08:17,14:47,15:47,22:17UTC. Actual source-observed
opening fills only09:30–11:30America/New_York, after the prior commitment.
The unfinished current bar is never placed in the completed-close cache. Closed
valuations are registered on the next actual collection, with quote date and
observation timestamp; missed valuation dates are flagged without backfilling.
The public monitor marks a missing scheduled publication after30minutes grace.
Sharpe requires20 actual contiguous daily observations; it is not fabricated
from initialization cash. No economic pass can authorize live trading; future
cost-stress/market-liquidity checks remain separate from the five base gates.
