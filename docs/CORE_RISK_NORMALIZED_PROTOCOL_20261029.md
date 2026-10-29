# Core risk-normalized ranking: fixed experiment, 29 October 2026

## Decision and prior work

Main at 0826ba0da499927d3b678e7da940808f4c9d27c0 preserves completed Core baseline, entry-stop and trailing-stop studies. Do not repeat these studies or tune their stops after inspecting their extension. PR 13 already tested ordinary and risk-adjusted 50/30/20 multi-horizon ranking with 25 slots, covariance sizing and different accounting. That is prior development evidence, not a new hypothesis or a passing model.

This experiment isolates one ranking change on the current, independently reconciled Core raw-price/PIT/dividend/whole-share engine: rank positive 12-2 momentum divided by the existing 63-return sample daily volatility. Keep the same eligible set, 253-session requirement, USD 10 floor, USD 5M ADV20, 15 slots, capped inverse-volatility sizing, SPY/SMA200 regime, monthly/reentry timing and next-open fills. Ticker breaks exact score ties. Do not add stock stops, return horizons, filters, retention buffers or parameter searches.

The economic hypothesis is that scaling ranking as well as position size can reduce selection of extreme-volatility winners. This idea is already used in published risk-adjusted momentum methodologies; this is an isolated Core implementation test, not a claim to invent it. No external index performance is evidence for this portfolio. Reference: https://www.indexologyblog.com/2024/07/09/sp-momentum-indices-leading-the-pack/ .

## Frozen evaluation

Use only the immutable core-risk-research-20261029 cache and manifest. Verify every file hash before calculation, forbid network in the replay process, and require the unchanged original Core source fingerprint. Reuse the ten previously completed baseline accounts as immutable controls; do not rerun their economic analysis. Report all five original merger-payment policies (locked and assumed 0/1/5/20 sessions) at both 15/30 bp per side. Assumed dates are never verified facts.

Run the candidate on 2024-01-01 through 2026-09-01, then resume each same account into 2026-09-02 through 2026-10-28. Preserve cash, holdings, claims, pending orders and benchmark across the boundary. Report both the complete account and the later segment. ALL dates have already been inspected by this project: both segments are DEVELOPMENT_RESEARCH, neither is an untouched holdout or forward paper. No post-result change is permitted within this experiment. Record all failed or data-blocked cases.

Keep the five economic gates exactly as momentum_core.gates. At least 30 complete monthly periods, positive net return, positive edge over SPY, daily maximum drawdown no worse than -20%, at least 50% positive months. A historical all-pass is only PAPER_ONLY; it is not robust GO or live authorization. All payment/cost sensitivities remain visible. Original vendor vintage, unverified merger payment dates and opening execution liquidity remain limitations.

## Independent verification and persistence

Separately reconstruct every signal's complete eligible population, score order, capped weights and SPY/monthly signal dates without importing the candidate selector. Independently reconcile cash/shares/claims/next-session fills/fees/NAV/SPY/metrics with the existing accounting auditor. Add adversarial tests that corrupt score order, weights or signal data and require rejection. Compare uninterrupted replay with checkpoint resume. Save protocol/code before calculating performance, per-case evidence and an append-only attempt register during calculation, and final summary/source/input fingerprints in GitHub. Preserve the full evidence in a separate unpublished release; no provider credentials or raw licensed prices belong in public artifacts.

No change to the frozen Core paper identity, production strategy, Buy Now or broker handling. live_approved=false and broker_orders_enabled=false always.
