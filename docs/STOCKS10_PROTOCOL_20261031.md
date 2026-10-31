# Stocks10 — separate, preregistered development study

Locked before the first replay, 2026-10-31. This is NOT H3 and must not
modify H3 source, accounts, history, scheduled collection or Buy Now.

User constraints: SEK 20,000 initial capital; ten individual common stocks,
at least one whole share per selected holding; no ETF/fund holdings. SPY is
only a regime observation and comparison account. Cash is permitted when
the existing daily SPY/200-close regime is off, and as an unavoidable lot
rounding residual. No leverage, fractional market purchases or live orders.

## First hypothesis A — feasibility before adding new rules

Removing H3's large SPY allocation may leave too much individual-stock risk.
Test that change directly: the existing formation-risk-normalized ranking,
ten equal 10% targets, monthly selection and existing daily global regime.
Use the existing point-in-time US common-stock universe, USD 10 floor,
USD 5m ADV20 floor and 253-session split-adjusted history. Preserve the
12–2 momentum formula and formation-window risk normalization. A stock
must fit one 10% capital slot including costs at the signal close. There is
no sector filter: historical PIT sector classifications are unavailable.

At the NEXT observed open, determine whole-share desired amounts. Reserve
one whole share in each of the ten PRECOMMITTED names first, then allocate
remaining cash toward equal weights. If minimum lots or quotes cannot be
funded/observed, block the rebalance atomically (including its sales) rather
than inventing a substitute, borrowing, omitting a holding or backfilling.
Corporate-action entitlements may be fractional and are labelled as such.
Risk off overrides the ten-position target and liquidates at next open.

## Conditional follow-up B — only if A is NO_GO

The H3 review verified that 11/15 latest names had negative one-month
returns: skipping the latest month can retain stale winners. If A fails,
test ONE prespecified eligibility change: require positive split-adjusted
21-session AND 63-session returns, with the same long-window score and
all other rules unchanged. Zero is an economic sign condition, not a fitted
cutoff. Do not search horizons, thresholds, stop distances or allocations.
Do not claim B is independent confirmation; both use reviewed history.

## Capital, costs and currency

Start with SEK 20,000 converted using the last ECB USD/SEK cross published
strictly before the first replay session. USD cash account thereafter.
Report USD and SEK values; daily SEK marking also uses strictly prior-date
ECB reference rates (not executable spot quotes). Reject stale (>7 days),
missing or nonpositive FX. Archive the downloaded ECB input and hash it.

Each order costs max(USD 1, 0.25% of notional) commission PLUS a conservative
0.25% currency-conversion allowance PLUS 15bp execution/spread allowance.
Stress uses 30bp execution allowance. These are disclosed research
assumptions, not a verified user's broker tariff. Charging the FX allowance
even with USD cash is conservative. No interest, tax advantage or free fills.
Dividend cash is available only on payment date. Retain existing corporate
action repairs, unpriced rights and confirmed suspension accounting.

## Evaluation and stop rule

Replay the saved 2024-01-01–2026-10-28 inputs offline. Reuse completed Core,
H3 and SPY results rather than rerunning their approved experiments.
Test all five existing unresolved-payment policies and both existing halt
marks at both costs: 20 scenarios per candidate, NOT independent markets.
Apply UNCHANGED five GO gates in USD, and also disclose SEK performance.
Report whole lots, missing-slot sessions, actual fees, liquidity, daily
drawdown, Sharpe, yearly results, signal timing and independent accounting.
NO_GO if ANY required scenario/gate/audit fails. A historical pass is at most
PAPER_ONLY; no reused dates are untouched out-of-sample observations.
No live-GO, broker orders or production replacement. All failed and blocked
cases remain visible. If A and B fail, stop rather than parameter hunt.

## Sources for assumptions

ECB: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html
(reference rates are informational, normally published around 16:00 CET).
Avanza FX fee explanation: https://blogg.avanza.se/kopa-utlandska-aktier-har-ar-allt-du-behover-veta/
Commission floor assumption is informed by, not asserted as today's tariff:
https://investors.avanza.se/media/press/2015/lanserar-ny-mobil-app-och-sanker-courtaget-pa-utlandshandel/
