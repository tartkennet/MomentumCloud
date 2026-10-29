# Accounting completions, not model tuning

The first fixed run [40843013763](https://github.com/tartkennet/MomentumCloud/actions/runs/40843013763)
correctly blocked all ten historical accounts at `Missing close SOVO 2024-03-12`.
The extension accounts therefore had no historical checkpoint. No completed
candidate performance was inspected or approved. Its complete attempt register
is retained alongside this document and in the unpublished release
`core-normalized-research-40843013763`.

SOVO's closing 8-K states that its merger became effective at 8:05 a.m. on
12 March 2024 and each ordinary share converted to a USD 23 cash entitlement:
https://www.sec.gov/Archives/edgar/data/1856608/000110465924033282/tm248409d1_8k.htm .
Nasdaq independently confirms the halt and pre-open close:
https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2024-107 .

SOVO and other documented cash acquisitions were already present in PR 13's
`backtest_momentum_v3.py` at f84cc484402cbdf054104cdfd63de9db5aaa6f04, but
absent from the narrower frozen Core event map. `research_core_actions.py`
preserves twelve such post-2023 events with rechecked primary sources, without
changing the frozen Core or its paper identity. It records actual fixed
entitlements, never fictional market fills. The RGLS contingent right remains
unpriced with zero carrying value and separately disclosed contractual maximum.
Payment dates remain unverified. Every original payment-delay scenario applies
to these events as well. No stock is excluded to avoid an event.

Before reusing old controls, the runner checks their complete trade and target
exports and blocks if a supplemented symbol occurs. That conservative condition
proves these additional facts cannot change the saved baseline portfolios.
If it fails, the controls must be explicitly reconciled instead of silently
reused. The raw input manifest and all 1,001 archived price/reference/event
files remain unchanged. Supplementary facts are included in the new study hash.
Ranking, weighting, costs, dates and economic gates remain exactly frozen.

The first workflow also failed to push its summary from GitHub's synthetic PR
merge checkout. Evidence upload and unpublished release preservation succeeded.
The workflow now checks out the exact candidate head with full ancestry and
checks the branch has not moved before committing its report. It never force
pushes or overwrites concurrent work.

The second run 40843858260 retained a further missing quote for TGH on
2024-03-14. Its 6-K confirms that date's pre-open cash acquisition at USD 50:
https://www.sec.gov/Archives/edgar/data/1413159/000095017024031155/tgh-6k-03_14_2024.htm .
This thirteenth event is a new verified completion, not a PR 13 fact.
The second attempt register is preserved separately. Its report push succeeded.

A new preflight enumerates all potential held quote gaps over the entire
fixed window without computing NAV or performance. Known corporate events
transform the tracked sleeves; missing buys remain cash and unknown held
quotes block the actual replay. Scanning past an unresolved sleeve serves
only to collect other issues, never to create a financial result. The frozen
selection and risk rules are unchanged.

## Complete quote-coverage review

Run 40844588971 completed all 34 risk-on ranking dates without calculating
portfolio returns. It identified 24 remaining potential held-quote gaps; the
full preflight and input/source fingerprints are retained in that run's
artifact and unpublished research release. Twenty-one are now completed as
plain cash events in `research_core_actions.py`, with primary sources per row.
Together with the first thirteen completions, the research supplement has
34 events. No raw price is inserted, no security excluded, no pay date guessed.
RDUS, TGI and EA distinguish their legal closing dates from the next
non-trading session used by the start-of-session ledger.

The next preflight independently reconstructs every complete eligible
population and verifies all signal dates, score order and weights, even if
the financial replay remains data-blocked. It must not substitute a partial
return or a zero for the blocked account.

Three cases require explicit new accounting support, not another ranking:

| Case | Verified facts | Required implementation |
|---|---|---|
| AEL | Closed 2024-05-02; trading suspended before 2024-05-03; USD 38.85 plus 0.45464 BAM shares per AEL share | Book stock AND cash consideration, preserve fractional BAM entitlement and payment-delay sensitivities; independently audit both legs |
| PLYA | Trading suspended 2025-06-16; non-tendering holders' corporate reorganization on 2025-06-17; USD 13.50 consideration | Resolve the intervening suspended security valuation explicitly; never move the merger back one day or invent a 2025-06-16 market quote/tender instruction |
| RNA | Avidity renamed RNA to RNAM on 2026-02-26; one Atrium share per ten Avidity shares; Atrium begins trading under reused RNA on 2026-02-27; RNAM acquired for USD 72 before that session | Separate the two issuer identities, retain both cash and spin-off stock entitlement, and validate quote/ex-distribution timing; never join Avidity history to Atrium |

Primary sources:

- AEL: https://www.sec.gov/Archives/edgar/data/1039828/000110465924056427/tm2413201d1_8k.htm
- PLYA reorganization: https://www.sec.gov/Archives/edgar/data/1692412/000164117225015857/xslSCHEDULE_13D_X01/primary_doc.xml
- PLYA suspension/tender timetable: https://www.sec.gov/Archives/edgar/data/1468174/000110465925058026/tm2517598d1_ex99a5g.htm
- Avidity/Atrium exchange notice: https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-89
- Nasdaq explicit prohibition on carrying Avidity history into Atrium: https://classic.nasdaqtrader.com/TraderNews.aspx?id=DTN2026-2
- Atrium distribution filing: https://www.sec.gov/Archives/edgar/data/2093101/000119312526083227/d87849d8k.htm

This is a recorded accounting boundary. It does not reject the candidate on
financial results: the candidate's full performance has not yet been computed.
The original 60 verified risk-study accounts remain untouched; a new event
cannot be assumed irrelevant to those controls without the isolation check.
