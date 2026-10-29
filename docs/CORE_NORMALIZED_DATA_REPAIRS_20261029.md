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
