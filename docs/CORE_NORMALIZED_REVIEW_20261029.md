# Core risk-normalized ranking — 29 October 2026

All observations are previously inspected development history. No live approval.

Study fingerprint: `3663c81f2ceafab040d90d4e9340c99185b8bdfe2dc60c5b940b8f0988d9021a`.

| Phase | Payment policy | Cost/side | Candidate net % | Baseline net % | Candidate drawdown % | Failed gates |
|---|---|---:|---:|---:|---:|---|
| historical | locked/last_quote | 15 bp | 32.0809 | 44.3054 | -8.0959 | beats_spy |
| historical | locked/last_quote | 30 bp | 30.6322 | 39.5403 | -8.1022 | beats_spy |
| historical | assumed_0/last_quote | 15 bp | 65.7328 | 25.4550 | -20.9158 | drawdown |
| historical | assumed_0/last_quote | 30 bp | 58.5954 | 19.6860 | -21.0355 | beats_spy, drawdown |
| historical | assumed_1/last_quote | 15 bp | 65.7836 | 25.5111 | -20.9340 | drawdown |
| historical | assumed_1/last_quote | 30 bp | 58.6678 | 19.5816 | -21.0350 | beats_spy, drawdown |
| historical | assumed_5/last_quote | 15 bp | 66.6515 | 25.5111 | -20.9409 | drawdown |
| historical | assumed_5/last_quote | 30 bp | 59.2860 | 19.5816 | -21.0143 | beats_spy, drawdown |
| historical | assumed_20/last_quote | 15 bp | 72.2034 | 26.7342 | -20.9462 | drawdown |
| historical | assumed_20/last_quote | 30 bp | 65.2914 | 21.6293 | -21.0078 | drawdown |
| extension | locked/last_quote | 15 bp | 31.8982 | 37.3148 | -8.0959 | beats_spy |
| extension | locked/last_quote | 30 bp | 30.4579 | 32.1977 | -8.1022 | beats_spy |
| extension | assumed_0/last_quote | 15 bp | 61.5497 | 15.5524 | -20.9158 | beats_spy, drawdown |
| extension | assumed_0/last_quote | 30 bp | 54.3098 | 10.3737 | -21.0355 | beats_spy, drawdown |
| extension | assumed_1/last_quote | 15 bp | 61.5988 | 15.6025 | -20.9340 | beats_spy, drawdown |
| extension | assumed_1/last_quote | 30 bp | 54.3836 | 10.2767 | -21.0350 | beats_spy, drawdown |
| extension | assumed_5/last_quote | 15 bp | 62.4793 | 15.6025 | -20.9409 | beats_spy, drawdown |
| extension | assumed_5/last_quote | 30 bp | 55.0710 | 10.2767 | -21.0143 | beats_spy, drawdown |
| extension | assumed_20/last_quote | 15 bp | 67.8847 | 16.3911 | -20.9462 | beats_spy, drawdown |
| extension | assumed_20/last_quote | 30 bp | 60.9240 | 11.9779 | -21.0078 | beats_spy, drawdown |
| historical | locked/offer_value | 15 bp | 32.0809 | 44.3054 | -8.0959 | beats_spy |
| historical | locked/offer_value | 30 bp | 30.6322 | 39.5403 | -8.1022 | beats_spy |
| historical | assumed_0/offer_value | 15 bp | 65.7328 | 25.4550 | -20.9158 | drawdown |
| historical | assumed_0/offer_value | 30 bp | 58.5954 | 19.6860 | -21.0355 | beats_spy, drawdown |
| historical | assumed_1/offer_value | 15 bp | 65.7836 | 25.5111 | -20.9340 | drawdown |
| historical | assumed_1/offer_value | 30 bp | 58.6678 | 19.5816 | -21.0350 | beats_spy, drawdown |
| historical | assumed_5/offer_value | 15 bp | 66.6515 | 25.5111 | -20.9409 | drawdown |
| historical | assumed_5/offer_value | 30 bp | 59.2860 | 19.5816 | -21.0143 | beats_spy, drawdown |
| historical | assumed_20/offer_value | 15 bp | 72.2034 | 26.7342 | -20.9462 | drawdown |
| historical | assumed_20/offer_value | 30 bp | 65.2914 | 21.6293 | -21.0078 | drawdown |
| extension | locked/offer_value | 15 bp | 31.8982 | 37.3148 | -8.0959 | beats_spy |
| extension | locked/offer_value | 30 bp | 30.4579 | 32.1977 | -8.1022 | beats_spy |
| extension | assumed_0/offer_value | 15 bp | 61.5497 | 15.5524 | -20.9158 | beats_spy, drawdown |
| extension | assumed_0/offer_value | 30 bp | 54.3098 | 10.3737 | -21.0355 | beats_spy, drawdown |
| extension | assumed_1/offer_value | 15 bp | 61.5988 | 15.6025 | -20.9340 | beats_spy, drawdown |
| extension | assumed_1/offer_value | 30 bp | 54.3836 | 10.2767 | -21.0350 | beats_spy, drawdown |
| extension | assumed_5/offer_value | 15 bp | 62.4793 | 15.6025 | -20.9409 | beats_spy, drawdown |
| extension | assumed_5/offer_value | 30 bp | 55.0710 | 10.2767 | -21.0143 | beats_spy, drawdown |
| extension | assumed_20/offer_value | 15 bp | 67.8847 | 16.3911 | -20.9462 | beats_spy, drawdown |
| extension | assumed_20/offer_value | 30 bp | 60.9240 | 11.9779 | -21.0078 | beats_spy, drawdown |

The historical boundary is 2026-09-01; extended rows retain the same account through 2026-10-28.
Later-segment metrics are preserved separately in the JSON; neither segment is an untouched holdout.
All five payment policies and both costs are retained. Assumed merger payment dates are unverified.
Independent ranking/timing and accounting checks validate implementation, not independent market evidence.
Vendor backfill, unverified payment dates, opening liquidity and actual execution costs remain limitations.
The five existing gates and original Core paper identity are unchanged. No parameter is selected after results.


## Fixed display case: assumed 5-session payment, 15 bp/side, last-quote halt mark

| Account | Net % | Daily drawdown % | Daily Sharpe, RF=0 | Actual fees USD |
|---|---:|---:|---:|---:|
| Normalized | 62.4793 | -20.9409 | 0.8428696398097738 | 6550.67 |
| Core control | 15.6025 | -47.3774 | 0.34667256037429345 | 5701.84 |
| SPY | 68.0753 | -18.4922 | 1.2933827496517174 | 149.60 |

| Calendar period | Normalized % | Core % | SPY % | Normalized drawdown % | Normalized Sharpe |
|---|---:|---:|---:|---:|---:|
| 2024 | 25.8619 | 8.8957 | 25.8660 | -13.9433 | 1.243118074499103 |
| 2025 | 14.5197 | -12.4374 | 17.3690 | -20.9409 | 0.6378729510638412 |
| 2026 | 12.7259 | 21.2377 | 13.7737 | -15.3297 | 0.7312242096680173 |

The display case is not a selected approval scenario: all 40 marking/payment/cost/phase results remain above and in JSON.
No fresh out-of-sample history exists in these previously reviewed inputs. The later segment is reported separately, without relabelling it.
