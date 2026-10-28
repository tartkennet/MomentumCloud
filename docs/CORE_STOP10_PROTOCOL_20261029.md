# Fixed Core risk experiment — 29 October 2026

The cash-timing study is complete. An independent daily dollar attribution
reconciles every NAV change and the USD 68,692.86 peak-to-trough loss in the
five-session assumed-payment case. Loss contributions include RNA, EBS, CATX,
RDW and RKLB. This does not justify excluding those names retrospectively.

## The only candidate change

Test the already existing v4 10% entry-loss threshold with the Core ledger.
This is one predefined risk hypothesis, not a threshold grid. Keep the same
12–2 ranking, historical universe, price/liquidity requirements, inverse-vol
weights, 10% target cap, SPY regime, monthly timing, fees and five gates.

Track the weighted average actual raw entry price, excluding fees. Partial
sales retain the remaining basis; additions average the basis. Splits and
verified stock exchanges transform basis without creating a loss. At a close
at or below 90% of basis, sell available whole shares at the NEXT observed
raw open, paying the ordinary cost. A gap can lose more than 10%. No fill at
the trigger price is manufactured. Missing held sale prices block the run.
Cash mergers cancel a pending stock sale and retain the existing cash/CVR
accounting. Non-tradable fractional shares are not sold at an invented price.

Stopped sleeves remain cash. Do not replace them using tomorrow's information
or rebalance other holdings. A stopped security cannot be repurchased within
the same calendar month, including a regime recovery. It may be ranked again
at the next month's ordinary signal. Stops take precedence on a rebalance
signal date. This policy applies to every security, not named losers only.

## Evidence fixed before candidate performance

1. Reproduce both original base/stress results and base exports exactly before
   evaluating the candidate. Core's published source fingerprint must match.
2. Historical experiment: 2024-01-01 through 2026-09-01. Run baseline and
   candidate at 15/30 bps per side under the SAME five payment policies:
   original indefinite unavailability, and assumed 0/1/5/20 trading sessions.
   Those payment dates are assumptions; fixed cash entitlements are verified.
3. Fetch and preserve the extension through 2026-10-28 only AFTER this source
   and protocol are committed. Resume each matching account from 2026-09-01;
   do not restart the capital or pick a winner before extension testing.
   Preserve every candidate/policy/cost result, including failures.
4. The extension is a newly replayed Core segment, NOT a certified untouched
   holdout or forward paper record. Earlier project work saw current market
   snapshots. The inspected historical period remains DEVELOPMENT. Record
   incremental extension returns and daily drawdown separately, without
   treating its short duration as 30 independent monthly observations.
5. Check independent cash/share/receivable arithmetic and all stop signals,
   fills, fees, split/merger basis handling, serialization and future-data
   invariance. No source adjustment based on performance is allowed. Fixing
   a demonstrated implementation or data error must preserve prior attempts.
6. Do not weaken gates or select the best settlement assumption. A historical
   pass is PAPER_ONLY with live_approved=false. No broker or Buy Now connection.
   If the fixed change fails, preserve that failure; do not tune until PASS.

The original Core model/paper identity is unchanged. This research candidate
has its own source/experiment fingerprints and result namespace. Full source,+inputs and output evidence must be preserved for offline reproduction.

Order limitation source: SEC, [stop order bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15).
