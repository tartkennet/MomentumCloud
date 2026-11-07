# BEST v2 — implementation status and verified source block

Recorded 2026-11-07 UTC for issue #50. This is NOT a trading approval.
Branch: momentum-best-v2-50. Draft PR: https://github.com/tartkennet/MomentumCloud/pull/51
Verified implementation revision: 0346e83bc0195f50e7c5af6bc04c1099dd75667c.

## Saved implementation
Separate v2 protocol, full-universe price inventory, seven-component momentum/
acceleration/volume score, low-volatility and price-pin/gap/overextension
diagnostics, economic business-sector classification and sector/factor/
correlation constraints. No ticker blacklist. The economic taxonomy derives
from archived provider business descriptions and detailed SIC, with healthcare
business overrides; it is not a claim to licensed GICS data.

Whole-share funding selects names first, defaults to max(SEK 25,000, independently
audited risk-constrained minimum), permits higher capital, and cannot replace
names to fit a budget. New code has separate controller, state names, encrypted
recovery cache, immutable publisher branch, API and five-tab UI. V1 helpers are
reused as numerical/accounting libraries; previous strategy files and journals
are not modified. No v2 state or trade has been published or initialized.

Prospective automated orders require complete source review, reconciled funding
and pre-opening integer commitments. Cash plans are not executed holdings.
No real broker, real orders or economic GO.

## Verified tests
- Production CI run 42316964131: PASS; 340 Python tests and JavaScript suites,
  including nine new v2 numeric/financial/source regressions and v2 API isolation.
- V2 run 42316964116, browser job 128231837592: PASS at 1440, 390 and 320 px;
  all five tabs, no page overflow/JS errors, identical ten fixture names after
  capital changes and reload.
- The 320px capital-card issue found by the browser test was fixed in v2-only
  CSS. Browser checks use the runner's documented preinstalled Chrome.
- These browser trades/data are explicitly synthetic fixtures. They are never
  copied to an actual journal. They do not certify production or real execution.

## Actual market-data gate: BLOCKED
Completed price inventory dated 2026-11-06:
5,312 provider reference records, 1,743 complete liquid unique issuers,
146 candidates meeting the v2 strong-price rules. All were assessed without
a top-100 ADV restriction.

The considered candidate SN (SharkNinja, CIK 0001957132) requires original 6-K
coverage. The complete index contains such filings, but:
- direct original SEC access returns HTTP 403, including a declared public
  repository-contact User-Agent;
- the authenticated existing provider original-file path returns HTTP 404 and
  its corresponding file listing is empty;
- the documented material-text endpoint explicitly queried for 6-K and 6-K/A
  returns zero rows, despite indexed required filings.

Example indexed original:
https://www.sec.gov/Archives/edgar/data/1957132/0001628280-25-049846.txt
(filed 2025-11-06; inside the registered 400-day review window).

Receipts:
https://github.com/tartkennet/MomentumCloud/actions/runs/42315465927
https://github.com/tartkennet/MomentumCloud/actions/runs/42316722926
The v2 technical release gate fails correctly. Empty financial-only/8-K-only
coverage is never interpreted as absence of M&A. SN is not silently discarded
or replaced to force ten. A 400-day lookback is not relaxed after seeing results.

The 8-K event index and parsed text DO work using the existing market-data
credential. That does not establish 6-K coverage. The provider updates parsed
filings daily, so no realtime/unfiled-announcement coverage is claimed.

## Deployment and execution
Main remains 7d3ee3b (BEST v1). PR #51 is draft and unmerged. V2 has not replaced
the root or been published to Vercel production. Its new scheduled workflow is
not active on default main; Monday execution is NOT promised.

There is no technically approved final ten-name basket, live-data allocation,
verified SEK minimum, actual sector allocation or first v2 fill timestamp.
No historical/future fill is invented. The SEK 25,000 setting is a tested funding
policy, not a certified capital requirement for a completed live basket.

## Concrete remaining work
1. Obtain readable, identity/date-matched required non-8-K originals or an
   actually complete verified material-text source, preserving public dates,
   hashes and cached receipts. Do not waive the source gate or blacklist SN.
2. Rerun the resumable v2 market gate and independent selection/funding/order/
   ledger audits; only a PASS can certify ten real names and quantities.
3. Verify enabled default-branch Actions and pre-opening commitments; publish
   the separate v2 account and test its production API/mobile views.
4. Promote v2 to root only after those checks; retain prior models/history.
   The first observed future execution can occur only in the allowed NY window.

The local executor disconnected during this work. Tracked code, tests, protocol
and diagnostics were rescued through the GitHub connector; nothing essential
depends on an unsaved local draft. Original source snapshots remain in the
existing encrypted Actions recovery caches/artifacts, never in source commits.
