# One formation-risk normalization hypothesis — fixed after PR 22

PR 22 is complete and merged at 30f19d8936fbdee60888d6d1d9a1c7430c78d621. All 40 accounts pass their accounting and selection audits; all fail the unchanged financial gates. The fixed 5-session/15-bp display case earns 62.4793% versus SPY 68.0753%, with -20.9409% drawdown and 0.84287 zero-RF Sharpe. No thresholds are relaxed for that near miss. All old results remain preserved.

## Verified weakness and causal evidence

The current rank divides 12–2 formation return by just the latest 63 daily returns' volatility. Its numerator can retain a takeover announcement jump that has already disappeared from the shorter denominator. A stable post-announcement price then gets a large momentum score despite little remaining conditional upside. This mismatch is directly present in the first signal, 2024-01-02: SPLK has 75.1098% momentum, 0.442218% daily volatility, score 169.8478 and 10% target weight; SOVO has 56.2767%, 0.508766%, score 110.6141 and 10% weight. NVDA has 220.2767% momentum but lower score 104.3047. The saved raw signal prices are SPLK 152.28 and SOVO 22.04.

Cisco had publicly announced $157 cash for SPLK on September 21, 2023; Campbell had publicly announced $23 cash for SOVO on August 7, 2023. Those were conditional offers, not guaranteed proceeds. The conditional gross remaining upside at the signal was approximately 3.10% and 4.36%, respectively. Sources:
- https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2023/m09/cisco-to-acquire-splunk-to-help-make-organizations-more-secure-and-resilient-in-an-ai-powered-world.html
- https://www.thecampbellscompany.com/newsroom/news/campbell-to-acquire-sovos-brands-leader-in-high-growth-premium-italian-sauces/

These are documented examples of the rank defect, not proof that every loss comes from deals. No merger-status filter or list of retrospectively successful deals is introduced.

## Exactly one change

Keep the positive 12–2 return close[t-21]/close[t-252]-1. For RANKING ONLY divide by the sample standard deviation of the 231 daily simple returns wholly inside that SAME formation interval: close[t-i]/close[t-i-1]-1 for i=21,...,251 (newest-first indexing). Do not search risk horizons or select one on its result. The 231 observations follow arithmetically from the existing signal endpoints.

Keep current 63-return volatility for position sizing; keep the same universe, price/ADV/history rules, 15 slots, 10% target cap, inverse-volatility weights, SPY/SMA200 regime, signal dates, next-open fills, whole shares, corporate actions and costs. A zero/invalid formation-risk denominator is unrankable and disclosed. No named-stock exclusion, extra factor, stop or retention band. No cached provider prices or histories change.

## Full evaluation before further strategy work

Run all 40 fixed marking/payment/cost/phase accounts with the completed PR 22 ledger and independent auditor. Compare each matching scenario with the completed normalized candidate, original Core and SPY. Preserve all failures. Report net return, daily drawdown, zero-RF Sharpe, actual fees, calendar years and the separately resumed September–October segment. Do not pick a favorable cost/payment/marking convention for approval. Keep the same five GO gates exactly. Historical all-pass can only be PAPER_ONLY; no broker/live permission is created.

All available history has already been reviewed by the project. Neither the old nor new development results are certified fresh out-of-sample. Do not invent a holdout or future paper outcomes. A prospective test must freeze its own identity before the first observation and may only accumulate real later sessions.
