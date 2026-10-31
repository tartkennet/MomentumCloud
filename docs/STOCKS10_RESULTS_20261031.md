# Stocks10 — completed separate study, 2026-10-31

**NO_GO. No new forward account, broker orders, H3 replacement or Buy Now change.**

Source `fd019d6fe48cdefdc68d9788bf372c8682397a0f`, [run 41180905339](https://github.com/tartkennet/MomentumCloud/actions/runs/41180905339).
Artifact ZIP SHA256 `d83a119d3eb33779231770cff0771dccaccfb2ce1e16124236565790490c7790`. Permanent draft release `stocks10-research-41180905339-1`.

The original protocol was committed before replay. Both hypotheses and all failures are preserved.
This is reused development history, not untouched out-of-sample evidence.

| Case (5-session payment assumption, last quote, 15bp execution) | USD return | USD max DD | Sharpe USD | SEK return | SEK max DD | Fees USD |
|---|---:|---:|---:|---:|---:|---:|
| A | 6.39% | -45.03% | 0.27 | 5.28% | -53.93% | 722.84 |
| B | 35.44% | -29.80% | 0.47 | 34.02% | -37.44% | 885.30 |

## Interpretation

A removes the SPY core but fails drawdown, SPY outperformance and hit rate. B improves A, yet still fails drawdown and SPY outperformance. All 40 scenarios are NO_GO.
The small account magnifies minimum commissions and whole-lot rounding. B pays USD 885.30 (44.45% of initial USD capital over the full study; not an annual fee). Its average cash fraction is 20.83%, including defensive risk-off sessions. This is not a pure rounding-cost estimate.
Positive recent returns do not prevent correlated single-stock losses or gaps. No third indicator/threshold search is justified by these two reviewed-history results.
The final replay has ten positions of at least one share PLUS a fractional corporate entitlement. Do not call that exactly ten economic exposures. B retains 0.8934 CDE from the verified NGD exchange; A retains 0.232 COMP from an existing corporate exchange. These are not fractional market purchases or fictitious sales. They remain valued and auditable. This is an additional implementation issue before any real-world adoption.
The five original financial GO gates are applied in USD without changes. SEK drawdown is worse, not hidden by an FX switch. SPY comparison with the same small capital/retail costs returns +64.02% USD and +62.30% SEK; its SEK drawdown is -26.49%.

## Independent checks

All 40 strategy and 40 benchmark transaction/claims/NAV reconciliations passed; full eligible rankings were rebuilt independently; all 40 financial metric audits passed. The largest account error is below USD 0.000001. Same market vendor: this is independent code, not independent data-vendor confirmation.
Additional raw close quotes for the final holdings and SPY were fetched only for publication, then reconciled exactly to archived stock values. They did not enter any replay or select a model. The quote CSV hash is in the public evidence.
APGE initially blocked B at its real cash merger. Nasdaq and SEC confirm USD 135.11 and 2026-09-03 before-open completion. The unverified payment date is handled by all five frozen sensitivities. The interrupted first attempt is retained in `stocks10-research-41180505963-1`.

## Comparators and next step

Saved H3: +77.13% USD, -16.08% DD, Sharpe 1.31. Original Core: +15.60% USD, -47.38% DD. Their USD 100,000/15bp all-in assumptions differ from Stocks10 retail costs; they were not rerun or rewritten.
Keep H3 prospective collection unchanged. Stocks10 remains a completed rejected development study. No backdated trades or new paper returns are created. A future redesign needs a new economic protocol addressing portfolio risk, affordability and trading-cost feasibility, not tuning these two histories.
