# Momentum 10 v3 — issue #33, preregistered selection research

Frozen before new economic outcomes. All 2024-01-02–2026-10-28 observations
are reviewed DEVELOPMENT, never untouched out-of-sample evidence. Preserve
H3, Stocks10 A/B, Momentum10 v2, fees, capital, GO thresholds and journals.

## Diagnosis before the intervention

Saved v2 monthly retention M1 returned 43.59%, DD -36.41%, versus same-account
SPY 64.02%; 433 orders cost USD 841.08. Quarterly M3 reduced orders to 217
and fees to USD 416.37 but return fell to 19.83%, DD -52.65%. Q10 improved
DD only to -29.83%; 48/56 stopped exits opened below the synthetic barrier.
Cost alone and a nominal 10% stop do not explain or cure the failure.
The attached baseline diagnostic reads completed states without replay:
all selected one-/three-month returns were positive, with median monthly
M1 signal returns 12.06% / 49.52%. A negative last-month filter alone is
therefore not a new hypothesis. Quarterly losses include correlated space
names LUNR/RCAT/RDW/RKLB at the 2025-03-11 regime exit, and NEON in October
2025. Closed order cash flows are a limited diagnostic, not full dividend-
adjusted performance attribution; corporate-event names are excluded.
The old score ranks 12–2 returns and omits the most recent month. A positive
recent-return gate does not replace this stale ranking or ensure a healthy
current price path. Nominal slot affordability and very small capital also
restrict diversification. No ticker-specific exclusions will be fitted.

## Three finite causal hypotheses, fixed order

R: replace ONLY the formation score/positive formation requirement with
current 126-session total PRICE momentum divided by sample daily return
volatility over the same 126 sessions. Include the latest observed close.
Keep positive 21/63-session returns, raw close >=USD10, 20-session dollar
ADV >=USD5m, complete 253-session history, PIT common-stock universe,
prior-date FX, per-slot one-share affordability and ten equal target slots.
Daily volatility for stops is still sample sigma63. Monthly retention,
no individual stop is the first contrast against saved v2 M1.

T: ONLY if R fails financial OR operational admission, add close > mean of
last 63 split-adjusted closes. This tests deterioration of the price path,
not another score horizon. No rolling/trailing exits are added: at normal
reselection stocks outside the selected ten exit at next observed open.

D: ONLY if T also fails, retain T and add a greedy risk-cluster guard.
For each ranked, affordable, non-blacklisted candidate compute Pearson
correlations using the prior 63 daily split-adjusted returns through signal
close. Edges are correlations >=0.70. Accept a name only when every
connected component among accepted names plus candidate has <=2 members.
Continue down the same fixed ranking until ten names or exhaustion. No
absolute-correlation rule, sector hindsight, changing threshold or fitted
cluster count. This limits strongly co-moving clusters, NOT a guarantee of
industry/sector weights. Historical classifications are absent from saved
inputs. Provider overview documentation itself warns that historical
fundamentals can be dated by report period before filing availability:
https://massive.com/docs/rest/stocks/tickers/ticker-overview
Do not inject today's SIC/GICS into past signals. Disclose sector identity
as unknown; measure causal return clusters and broad name-based industry
hints only, explicitly unverified and NEVER a selection input.

Each activated selection stage has 20 frozen accounting/cost sensitivities.
Then evaluate the last activated stage over exactly the prescribed 3x3
matrix: intervals 1/2/3 calendar months (January anchored) x none/fixed10/vol.
Reuse its completed monthly/no-stop cases instead of replaying them.
This is a finite registered comparison, not selection of highest Sharpe.
Publication/admission priority: R before T before D if admitted; within the
last stage M1-none, M2-none, M3-none, M1-fixed10, M2-fixed10, M3-fixed10,
M1-vol, M2-vol, M3-vol. No fourth adaptive alpha hypothesis in this register.
A failure after D exhausts the supported mechanisms in issue #33; report
NO_GO and the residual problem, without an unlimited parameter search.

## Execution, stops, accounting and acceptance

Reuse frozen v2 retention/event/native-dividend/whole-lot implementation
without editing it. Keep intersections unchanged; exits and new entrants
only, one share in each entrant reserved before cash allocation. Next
observed opening fills, full costs, no borrowing/fractional market orders.
SEK20,000 initial, archived strictly prior-date ECB conversion; same FX
basis for SPY. No ETF/SPY equity purchases (SPY remains daily regime/benchmark).
Daily global SPY/SMA200 regime is unchanged. Missing ten eligible names,
missing opens, or unaffordable complete baskets are explicit failures.

The frozen v2 stop semantics are reused exactly: gross actual entry open
reference; fixed10 barrier 90% entry; vol distance 2*sigma63*sqrt(21), locked
at entry, nonpositive barriers flagged. Split/dividend/corporate adjustments
preserve economic basis. Observe CLOSE <= barrier, sell only at next
actual observed open at that open less costs, including adverse gaps.
These are daily-close synthetic stops; saved bars have NO intraday high/low.
After a stop hold cash, blacklist until next ordinary selection; no instant
replacement or same-close repurchase, including regime re-entry. Continuing
qualifying names keep quantities and entry basis. Corporate fractional
rights remain explicit, never fictitiously sold or hidden as cash.

Retail costs per order max(USD1,0.25% notional)+0.25% FX reserve+15bp
execution, stressed30bp. No free USD account assumption. Same five merger-
payment policies x two halt marks x two costs. Use only authenticated
1001-file cache, original ECB file, APGE completion and native TD repair.
No fresh price fetches or changed archived inputs. New symbols with
unreconciled corporate actions block publication rather than invent prices.

Independent audit imports NO v3 model: reconstruct selection using raw PIT
universe/history, score, SMA, correlation graph and full ranking; reuse
independent v2 policy audit with an independent population adapter and
independent selection guard, never the strategy selector. Reconcile cash,
shares, raw opens, fees, claims/native FX, daily NAV, retention, calendar,
stops, blacklist, and financial metrics. Same vendor is not independent data.
Export return, DD, Sharpe, monthly hit, costs, turnover, stop gaps, drawdown
periods, signal concentration/correlation and market-period results. Preserve
all failures, source hashes and checkpoint evidence in a separate release.

Unchanged USD financial gates in ALL20 sensitivities: >=30 complete monthly
intervals; net return>0; edge vs same-account SPY>0; max DD>=-20%; positive
monthly interval rate>=50%. Paper minimum additionally: every independent
check PASS, no missing/unfunded/less-than-ten basket, no extra/subwhole
corporate equity rights, no unresolved/nonpositive stop basis, maximum
order participation <=1% observed daily volume. No historical test permits
live GO. A qualifying candidate is at most PAPER_ONLY; its forward source
must be frozen and separately journalled before any actual future session.
Never backfill missed sessions, enable broker orders or change H3/Buy Now.

## Technical addendum — RAPT corporate event, unchanged selection

First registered run 41196548955 (source 1f6a077f5ada25eda13731fec66a4034f398cc2c)
blocked before any completed new outcome: RAPT missing close 2026-03-03.
Nasdaq ECA2026-124 confirms merger before that opening, USD58 cash per
share, last trading 2026-03-02. GSK's dated completion announcement/SEC6K
corroborates completion. Add only this v3 study's in-memory cash-event view.
No actual broker payment timestamp is known: preserve all five unchanged
payment sensitivities, including indefinitely locked claims. Never invent
a missing open/close or a sale; original cached files and all old sources
remain untouched. Re-run the blocked experiment, no completed cases existed.
https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-124
https://www.gsk.com/en-gb/media/press-releases/gsk-completes-acquisition-of-rapt-therapeutics/
https://www.sec.gov/Archives/edgar/data/1131399/000165495426001801/a1763v.htm
