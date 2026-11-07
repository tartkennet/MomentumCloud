# BEST v2 — saved prospective implementation and release gates

Updated 2026-11-07 UTC, issue #50 / PR #51. PAPER_EXPERIMENT, economic NO_GO.
No broker client or real orders. Main remains BEST v1 until independent data,
funding, enabled automation and separate production publication are verified.

## Current implementation

Full available XNAS/XNYS/XASE common-stock inventory, not top-100 turnover.
Price strength, relative strength, acceleration, volume, risk-adjusted momentum
and persistence; 253-session history, USD10 price/USD20m ADV20 minimums.
Generic low-volatility, pinning, jump and overextension controls; original-source
corporate-event review. No company eligibility blacklist.

The owner amendment in d732489 removes hard sector/factor count and capital
caps and any implied five-sector minimum. Strong names are selected before
capital; issuer 15% and correlation-component three-name/35% controls remain.
Sector count affects sizing softly and concentration is disclosed. Default
funding max(SEK25,000, independently audited minimum), reserve one whole share
of each first, allocate residual feasible lots. Browser capital never changes
ranked membership or the actual funded cohort.

E1 is separately preregistered, applied to all liquid issuers and WATCHLIST ONLY.
The actual APP mechanism check and limitations are in BEST_V2_APP_DIAGNOSTIC.md.
E1 did not identify APP earlier in the fully covered 126-session window; no
threshold was changed to force inclusion and no hypothetical trade was booked.

## Source access repairs

SN's previously blocking 6-K is now CLEAR using its complete official issuer
PDF (71 pages, all four material exhibits), pinned hash and source receipts.
STGW's missing parsed 8-K/A is verified against the SEC original/index using a
pinned complete public HTML copy. Financial filing queries use issuer CIK
rather than reused tickers and the legacy endpoint's compact YYYYMMDD dates.
Completed past mergers and distant unrelated conversions are not interpreted
as a pending issuer cash acquisition.

TBBB has missing provider SIC metadata; its primary grocery business supports
Consumer Staples without a ticker exception. Its 12 required 6-K filings and
all 19 narrative/exhibit originals have verified public copies. The legacy
financial service returns no TBBB annual records, so the indexed 20-F and its
20-F/A are required via the same original-identity/hash controls, including all
11 narrative/certification documents. Inaccessible originals still block
formation; stronger unknown candidates are not skipped to force ten.
See BEST_V2_SOURCE_MIRRORS.md, data/filing_mirrors.json and Actions source probes.
No API credential is committed or sent to public mirror hosts.

## Verified checks versus actual activation

348 Python unit tests pass locally, including 17 v2 financial, signal, source,
whole-share, automation and ledger tests. JavaScript regression suites pass.
The five-tab browser fixture passes at 1440, 390 and 320 px with no overflow or
JS errors; low/high capital and reload preserve membership. Fixture trades
are synthetic and never enter a published account.

Real 2026-11-06 full-universe checks cover 5,312 provider reference records,
1,743 complete liquid unique issuers and 146 strong-price candidates. This is
actual observed provider coverage, not a claim that inaccessible/unlisted
securities or incomplete histories were analyzed. Independently recomputed
population, metrics, ranking, funding, orders and accounts must all pass.
The latest actual release result is authoritative in the PR Actions checks;
unit/browser PASS alone is not a source or funding approval.

New account/state, encrypted recovery inputs, append-only journal branch and
API are isolated from BEST v1, H3, Avanza and Quality. Previous strategy source
and recorded histories are unchanged. Orders are precommitted before a future
opening and require observed positive-volume raw prices in 09:30–11:30 NY;
missed windows are never backfilled. Daily risk, monthly retained membership,
fees, cash, FX and observed NAV use independent reconciliation.

The default-branch workflow must prove its state is active, bind the proof to
its source SHA and publish the separate account before root promotion. Opening
attempts include 14:32/14:52 and 15:32/15:52 UTC; GitHub scheduling can be delayed.
Monday 2026-11-09 first potential 09:32 NY observation is conditional on real
prices and all gates, never an assumed or retrospectively booked fill. No first
actual v2 fill timestamp exists while it is still Saturday.
