# Momentum10 v2 — frozen retention / frequency / stop study

Registered BEFORE any v2 outcome. Separate from H3 and completed Stocks10 A/B.
No production strategy, source archive, paper history or Buy Now change.

## Verified problem and limited design

Stocks10 B main case paid USD 885.30 over 709 sessions (44.45% of initial
USD capital), with 491 transaction/event rows. Net +35.44%, DD -29.80%,
Sharpe .47, versus same-account/cost SPY +64.02%. A was worse. Prior source
and results remain immutable. Reweighting continuing names is unnecessary
for a membership strategy; costs and whipsaws are testable mechanisms.

Exactly FIVE primary economic attempts, each at the same 20 accounting/cost
sensitivities as before. NOT a 3x3 search for the best historical combination:

* M1: monthly, retention, no individual stop.
* M2: every second calendar month, retention, no individual stop.
* M3: quarterly, retention, no individual stop.
* Q10: quarterly, retention, fixed 10% close-based stop.
* QV: quarterly, retention, entry-volatility-scaled close-based stop.

The quarterly anchor is chosen for the stop comparison BEFORE results,
because the verified problem is expensive turnover. No stop thresholds,
volatility windows, month phases or ranking parameters will be swept.
Eligible publication priority is M3, Q10, QV, M2, M1 (fewer ordinary
selections first, then simplest stop), NOT maximum historical Sharpe/return.
Every alternative and rejection is retained and clearly labelled development.

## Unchanged selection and capital

SEK 20,000, prior-date ECB cross into a USD cash account, same dated FX for
SEK reporting. Ten common-stock targets; no ETF/fund holdings; SPY only
regime observation and comparison account. Keep the exact Stocks10 B
formation-risk-normalized 12–2 score, positive 21/63-session eligibility,
PIT universe, price/ADV/history and one-share signal-slot affordability.
This isolates new execution/risk principles; no new alpha indicator.

M1/M2/M3 ordinary selection: first observed close of months anchored at
January, with `(month-1) % interval == 0`. Existing daily SPY/200-close
regime remains. Genuine risk-on re-entry can start a new basket outside
the ordinary calendar; record these separately. Every ordinary date
recomputes the full ranking, even when all ten names persist.

At next observed open sell ONLY whole shares of excluded names. Retain
all shares of names in the intersection unchanged: no routine topping up,
trimming or sell/buy round trips. Use proceeds plus available cash for NEW
names only, reserve one whole share in each first, divide remaining cash
equally among entrants, reduce largest proposed notional one share at a
time until fully funded. No borrowing, arbitrary replacement after an open
gap, receivable-funded purchases, fractional market orders or fictitious
prices. A missing open or unfundable complete basket blocks that ordinary
rebalance atomically and fails the operational requirement.

Corporate exchanges/dividends/splits use existing verified repairs plus
the study-only APGE completion. Fractional corporate entitlements are
preserved, valued and exposed; they are NOT secretly sold as whole shares
or labelled cash. More than ten economic equity exposures, unresolved
risk references, unfunded fills or liquidity >1% ADV participation block
paper eligibility even if financial gates pass. Ten target stocks does
not promise ten live holdings during defensive cash/stop intervals.

## Stops (synthetic daily-close decisions, not intraday broker orders)

Reference is the actual gross entry opening price, excluding fees.
Continuing retained holdings keep that original reference; there are no
ordinary top-ups. Fixed level = 0.90 * reference. QV entry distance =
`2 * stdev(previous 63 daily split-adjusted simple returns) * sqrt(21)`;
level = reference * max(0, 1-distance). A two-standard-deviation monthly
scale is selected once as a transparent risk unit, not an estimated loss
guarantee. Sigma uses data through the signal close, never the fill day.
Volatility and level are locked at entry: no trailing peak or daily
loosening. A nonpositive level is reported as ineffective protection.

Split divides reference and level by the split ratio. On an ex-dividend
date subtract the per-share dividend from level (total economic return,
not a mechanical price-drop trigger); it remains an unpaid receivable
until the payment date. Stock exchanges convert level/reference using
the contractual ratio, subtracting cash consideration from level first.
New spin-off assets without a defensible inherited stop basis are marked
unresolved and block paper admission; no basis is invented.

After each close, when close <= level, queue sale of ALL executable whole
shares at NEXT observed open, less the full cost function. Use that actual
open even for adverse gaps; never fill at the level itself. Fractional
corporate residuals cannot be market-sold. Global risk-off takes priority
and liquidates all executable whole shares. An already committed ordinary
selection at the same close may not override a triggered stop.

After an individual stop the slot remains CASH; no immediate replacement.
Exclude stopped names until the NEXT ordinary selection (including if a
global risk-on re-entry occurs sooner). That ordinary selection clears
the blacklist and may repurchase a name if it qualifies then, after the
new close and only at the next open. A new stop gets a new entry basis.
A stop on an ordinary selection date still prevents same-close repurchase;
its blacklist expires at the following ordinary selection.

## Costs, data, audit, recovery and admission

Same old fee: max(USD 1, .25% notional) commission + .25% FX reserve +
15bp execution allowance; stress 30bp execution allowance. USD cash does
not remove the conservative FX reserve. No interest/tax benefit.
Five existing merger-payment policies x two confirmed-halt marks x two
costs = 20 scenarios per attempt. No paid API or new market-data retrieval.
Use saved authenticated 2024-01-01–2026-10-28 cache and archived ECB input.
Reuse A/B, H3, Core/SPY comparators; never rerun their approved experiments.

Independent code reconstructs all cash, claims, corporate actions, shares,
raw opening fills, costs and NAV, and checks full PIT ranking, calendar,
stop levels/timing, retained quantities, stop blacklists and financial
metrics without importing the new strategy. Same vendor is NOT independent
data provenance. Report all scenarios, net USD/SEK return, DD, Sharpe,
gross turnover/average NAV/year, fees, normal vs stop vs regime trades,
adverse fill gaps, peak/trough recovery, and 21/63-session post-stop price
recovery as DESCRIPTIVE shadow observations only. Missing/delisted/end-of-
window shadow prices stay missing and cannot enter trading decisions.

Unchanged five GO gates, in USD, must pass in ALL 20 sensitivities:
>=30 whole monthly intervals; net return >0; net edge vs SPY >0;
DD >=-20%; positive-month rate >=50%. Paper minimum ALSO requires every
audit and operational constraint above. Reused history is DEVELOPMENT,
never untouched OOS; historical admission is at most PAPER_ONLY.
No prospective trades may be recreated in arrears, no broker orders/live-GO.

## Conditional next hypothesis C (one, not another search)

ONLY if all five primary attempts fail financial admission AND a DD gate
fails, test C: M3 retention without an individual stop plus a 10% annualized
ex-ante portfolio volatility budget. This tests the next verified portfolio-
risk mechanism, rather than adding a technical indicator. At selection
compute the 63-return equal-weight covariance risk of the ten B names,
annualize sqrt(252), exposure=min(1,.10/risk). Reserve ten whole minimum
lots first; if they cannot fit the risk budget block, never drop a stock.
At ordinary re-entry/reselection trim retained whole shares ONLY if their
notional exceeds the new per-name risk budget, retaining at least one;
never top up a retained name. New entrants share remaining risk-budget
cash after the retained marked value. Integer minima can cause realized
risk-budget deviations; disclose them, do not claim a hard risk cap.
This exception to routine retention is a labelled portfolio-risk action.
Same 20 sensitivities and admission. C is last in the frozen publication
priority. If C also fails, preserve exact economic/operational failure;
do not invent a seventh parameter variant or claim a model is finished/GO.

Sources: SEC stop execution warning (not a price guarantee):
https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15
Risk-budget motivation (not validation of this implementation/target):
https://www.nber.org/papers/w22208
