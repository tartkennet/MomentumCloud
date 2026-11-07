# BEST v2 — prospective protocol, issue 50

Registered before any v2 results are inspected. Hypothesis: established price
strength reinforced by recent relative acceleration and volume-supported price
strength can provide a useful prospective experiment when economic sectors,
correlations, overextension and corporate-event distortions are controlled.
No fitted historical performance target; economic NO_GO; PAPER_EXPERIMENT only.
V1 rules, code, cohort and journal remain unchanged.

## Universe and signal
All dated available active US common stocks on XNAS/XNYS/XASE, one CIK (highest
ADV20 then ticker), no ADV100 truncation, price >= USD10, ADV20 >= USD20m,
253 consecutive observed split-correct closes, positive recent volume.
All inputs must be available before the actual decision. Current observed
business metadata is admissible for a current prospective decision, never for
a historical replay. No vendor, event-source or publication failure means CLEAR.

Exclude annualized sample Vol63 < 8%; use max(Vol63,20%) in the risk-adjusted
score denominator. Exclude adjusted daily absolute jumps >=35% in the last 126 sessions pending verified
review; exclude last-21-close range <3% following a >=15% jump in 126 sessions
(price pinning diagnostic). Exclude close/SMA50 >1.35, 21-session return >60%,
or 63-session return >150% (overextension, not a fitted return rule).
Known pending definitive acquisitions involving cash, fixed exchange terms,
tenders, liquidation or price-binding distributions are not active momentum.
Classify from dated original SEC/issuer text and archived receipts, including
announcements and later termination/completion. No ticker blacklist. Ambiguous,
incomplete or inaccessible event evidence blocks the considered candidate and
formation; it is never silently counted as no event. Review annual/interim
filings and event filings since the prior annual filing (at least 400 days).
Retain document identity, acceptance time, coverage and exact content hashes.

M12_1=C21/C252-1 and M6_1=C21/C126-1; RS intervals divide gross returns by SPY.
RS63 and RS21 use current close. Acceleration = log(1+RS21) minus half of
log(relative gross return over sessions 21..63). Volume confirmation combines
current/prior-63-close high with mean recent-five dollar volume divided by mean
prior-20 dollar volume, capped at 3. Vol63 uses 63 daily simple returns, ddof=1,
sqrt252; persistence is 63-session fraction above own trailing SMA50.
Across all fully price-eligible unique issuers, midrank percentiles:
25% RS12_1 +20% RS6_1 +15% RS63 +10% acceleration +10% volume confirmation
+15% M6_1/max(Vol63,.20) +5% persistence. Exact rational composite ties use
RS63 descending, then ticker. No capital or fundamental quality enters ranking.

Strong: M12_1,M6_1,RS6_1,RS63,RS21 >0; close>SMA50>SMA200;
SMA50 and SMA200 both above their levels 21 sessions earlier; persistence>=.55.
Consider the first 60 strong names. Missing required reference evidence blocks,
never skip an unknown stronger name to force ten. Record every economic/risk
exclusion and its original global rank. No weaker pool expansion to fill ten.
Optional earnings reactions are diagnostics only if dated original facts exist;
missing earnings data never causes a score reweighting or invented reaction.

## Economic risk and funding
Verify an economic eleven-sector taxonomy with issuer business provenance,
including healthcare/life-science exposure even when SIC says software/services.
A broad SIC division alone is insufficient. Unknown or contradictory sector is
DATA_BLOCKED. Maximum two names and 25% reserved capital per economic sector;
one issuer and 15% per issuer; correlation connected components at rho>=.85
on 63 returns: maximum three names and 35% capital. Shared growth factor
(Technology+Communication Services) and rates factor (Financials+Real Estate+
Utilities) each maximum four names and 45% capital. Other sector factors remain
under their sector caps. Greedy descending frozen rank, exactly ten or explicit
insufficient strong breadth; no cap relaxation.

Select names first. Reserve >=one whole share each, 2% price limit buffer,
max(USD1,25bp) commission, 25bp FX, 15bp execution; round reserves up to SEK cents.
Minimum capital is max(total one-each reserves, each risk-group reserve/cap).
Default funded initial SEK=max(25000,verified minimum); 21000..27000 is a soft
preference, never a filter/ceiling. Larger whole shares target capped inverse
max(Vol63,.20) weights while reserving all ten first; deterministic under cash
and every risk cap. Publish quantities, actual reserve and leftover cash.
Browser capital changes never alter the ranked membership or booked capital.

## Separate prospective automation
New v2 model fingerprint, state, encrypted recovery cache, immutable observations,
publication branch and API. No old trades or curves are copied. New initialization
and ten exact buy quantities committed before a future opening. Only genuinely
observed positive-volume raw opening prices in 09:30..11:30 America/New_York;
no backfills, no broker. Planned Monday 2026-11-09 opening is conditional, never
an assumed fill. Explicitly verify enabled scheduled Actions before promotion.
Monthly membership, retain qualified selected holdings, sell departures first.
Daily SPY close>SMA200 risk; otherwise target cash at a permitted observed open.
Missing data pauses rather than fabricating a price or risk decision. Partial
baskets are explicit. Observed daily closes, events, fees and dated ECB FX drive
independently reconciled NAV after actual paper start. No simulated prehistory.
V2 may become root only after technical/data/funding/operational publication
verification. Prior models remain archived with unaltered journals and GO rules.

## Owner amendment 2026-11-07 — revision 2 (before any v2 cohort)

This section supersedes the earlier two-name/25% sector and four-name/45%
factor constraints. The owner explicitly removes those hard limits. No minimum
number of sectors is required. The ten strongest qualified names are selected
subject to one issuer and the unchanged price-correlation cluster control.
Sector/factor concentration is disclosed as a warning, never a reason to replace
a qualified stronger name with a weaker stock. Whole-share sizing uses
inverse max(Vol63,.20) divided by sqrt(selected count in the same economic
sector), normalized with the unchanged 15% issuer limit. There is no sector or
factor capital cap. The 35% correlated-cluster capital cap remains. Residual
cash is allocated by largest target-weight deficit while every integer-lot,
cash, issuer and cluster rule is satisfied. The SEK 25,000 target remains soft.
Earlier protocol revision is archived; no v2 account existed before this change.

## Separately preregistered early-turn component E1

Hypothesis: sustained positive short-term relative strength and a volume-backed
recovery after a material prior decline can identify confirmed turns before the
long SMA200 and lagged six-month return have recovered. This is an independent
prospective WATCHLIST component, not an automatic APP inclusion or an economic
GO. Established v2 membership is unchanged by E1 until a separate deployment
explicitly authorizes it. Apply identical E1 rules across the whole priced
universe, not only APP. All normal price/liquidity and pin/jump/overextension
filters still apply. No earnings reaction is invented when PIT events are absent.

Using only closes/volumes already observed on each evaluation date:
- prior drawdown=min(C[21:127])/max(C[21:253])-1 <= -15%;
- C0>SMA20>SMA50; SMA20>SMA20 ten sessions ago and SMA50>SMA50 ten sessions ago;
- RS21>=3%, RS63>0 and relative acceleration>0;
- >=8 of the latest ten closes above their own contemporaneous SMA20;
- C0>=99% of the prior 63-session highest close;
- recent-five/prior-twenty dollar-volume ratio >=1.2;
- annualized Vol63<=80%, C0/SMA20<=1.20, 21-session return<=40%;
- no normal v2 price exclusion (including Vol63<8% and unresolved jumps).

Rank E1 diagnostics across the whole eligible price universe by exact midrank
30% RS21 +25% RS63 +20% relative acceleration +15% volume confirmation
+10% SMA20 persistence over ten sessions. These weights and thresholds are fixed
before APP prices are inspected in this revision. Review APP's established-v2
rejection reasons and apply this same frozen E1 at each available date in the
last 126 observed sessions. A retrospective earliest signal is a mechanism
check, not evidence that an ex-ante registered strategy actually traded APP.
Missing 253-session history or volume is disclosed. Do not tune E1 to make APP
qualify and do not append hypothetical trades or returns to paper history.
