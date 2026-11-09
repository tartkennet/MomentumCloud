# Incident 61 — SEC access and fixed future order commitments

Evidence collected 2026-11-09; no retrospective paper fills.

## Exact failing request

Run 42703194540, job 129453052718, at 21:32:02 UTC:
PLSE (CIK 0001625101), 8-K/A filed 2026-03-02,
accession 0001437749-26-006269. Provider text index lacked this amendment.
The provider supplied:
https://www.sec.gov/Archives/edgar/data/1625101/0001437749-26-006269.txt

This omits the normal accession directory. The verified identity-bound archive
path is:
https://www.sec.gov/Archives/edgar/data/1625101/000143774926006269/0001437749-26-006269.txt

PR #55 already fixed the operational scope error: PLSE is not a committed
November holding. Previously the collector unnecessarily attempted a new daily
formation before retaining the existing month. Current locked-month handling
checks fresh prices, issuer identity and corporate-event evidence for ALL TEN
actual members, and independently audits retained original formation evidence.
Full-universe price coverage remains checked. New-month formation still requires
all original candidate evidence; an unknown candidate cannot be silently skipped.

## Actual independent transport probe

Read-only Actions run 42706896117, job 129465952019, 21:54:49–51 UTC:
original URL HTTP403; corrected canonical URL HTTP403; official
https://data.sec.gov/submissions/CIK0001625101.json HTTP403.
All returned a 4,818-byte HTML SEC automated-access denial page, not a filing.
No Retry-After header. Three sequential requests, one-second spacing. Existing
User-Agent: `MomentumCloud research (github.com/tartkennet/MomentumCloud)`.
No real contact email is configured; no invented contact or rotated identities
were used. These observations establish access denial from this runner; they
cannot distinguish IP reputation and User-Agent policy, nor prove rate limiting.
Correcting a URL does not establish access or a missing original's existence.
No bypass, arbitrary mirror, secret logging or false source clearance.

## Repair and remaining limitation

Recognized complete-submission paths are normalized using validated CIK and
accession identity. Hash-verified cached originals under the old URL are reused
without network; pinned, independently verified issuer originals remain first
choice. Cache integrity failures and SEC403 remain blocking. There is no cached
PLSE original proven by this probe. An uncached future candidate needing that
source remains blocked until an authenticated/allowed official source is verified.
That research limitation does not excuse failing checks for the committed ten.

The live paper engine and E2 policy are unchanged. Existing pending quantities,
limits and decision hash now remain fixed across new daily closes; no nightly
automatic resizing. Risk-off/month changes retain existing cancellation rules.
Order failures remain explicit, not alleged fills. Same ten, SEK25,000; no
journal or reconstructed portfolio rewrite. The reconstruction is a separate
hypothetical account and its after-close updater/theme/mobile UI are unchanged.

First configured eligible future slot: 2026-11-10 14:52 UTC =15:52 Stockholm,
09:52 New York, subject to GitHub cron delivery and actual verified delayed-minute
receipts. No scheduling SLA or execution guarantee. Market opens 15:30 Stockholm;
observed source is about 15 minutes delayed. Technical PASS is not trading success.
Monday's missed-session business check stays red after durable publication.
