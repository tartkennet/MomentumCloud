# Core risk-normalized ranking — 29 October 2026

All observations are previously inspected development history. No live approval.

Study fingerprint: `b64f5b4ce9da568f95c1cbba95ce5225ddd700fad1cc98c66a80db769911f0f4`.

| Phase | Payment policy | Cost/side | Candidate net % | Baseline net % | Candidate drawdown % | Failed gates |
|---|---|---:|---:|---:|---:|---|
| historical | locked/last_quote | 15 bp | 150.6381 | 44.3054 | -31.2368 | drawdown |
| historical | locked/last_quote | 30 bp | 139.4809 | 39.5403 | -31.9701 | drawdown |
| historical | assumed_0/last_quote | 15 bp | 148.3452 | 25.4550 | -35.1398 | drawdown |
| historical | assumed_0/last_quote | 30 bp | 137.3386 | 19.6860 | -35.1162 | drawdown |
| historical | assumed_1/last_quote | 15 bp | 148.3452 | 25.5111 | -35.1398 | drawdown |
| historical | assumed_1/last_quote | 30 bp | 137.3386 | 19.5816 | -35.1162 | drawdown |
| historical | assumed_5/last_quote | 15 bp | 148.3452 | 25.5111 | -35.1398 | drawdown |
| historical | assumed_5/last_quote | 30 bp | 137.3386 | 19.5816 | -35.1162 | drawdown |
| historical | assumed_20/last_quote | 15 bp | 149.7898 | 26.7342 | -34.6088 | drawdown |
| historical | assumed_20/last_quote | 30 bp | 138.9241 | 21.6293 | -34.4720 | drawdown |
| extension | locked/last_quote | 15 bp | 137.9345 | 37.3148 | -31.2368 | drawdown |
| extension | locked/last_quote | 30 bp | 126.8410 | 32.1977 | -31.9701 | drawdown |
| extension | assumed_0/last_quote | 15 bp | 129.4756 | 15.5524 | -36.2617 | drawdown |
| extension | assumed_0/last_quote | 30 bp | 118.4566 | 10.3737 | -36.6807 | drawdown |
| extension | assumed_1/last_quote | 15 bp | 129.4756 | 15.6025 | -36.2617 | drawdown |
| extension | assumed_1/last_quote | 30 bp | 118.4566 | 10.2767 | -36.6807 | drawdown |
| extension | assumed_5/last_quote | 15 bp | 129.4756 | 15.6025 | -36.2617 | drawdown |
| extension | assumed_5/last_quote | 30 bp | 118.4566 | 10.2767 | -36.6807 | drawdown |
| extension | assumed_20/last_quote | 15 bp | 130.6733 | 16.3911 | -35.7838 | drawdown |
| extension | assumed_20/last_quote | 30 bp | 119.9375 | 11.9779 | -36.0989 | drawdown |
| historical | locked/offer_value | 15 bp | 150.6381 | 44.3054 | -31.2368 | drawdown |
| historical | locked/offer_value | 30 bp | 139.4809 | 39.5403 | -31.9701 | drawdown |
| historical | assumed_0/offer_value | 15 bp | 148.3452 | 25.4550 | -35.1398 | drawdown |
| historical | assumed_0/offer_value | 30 bp | 137.3386 | 19.6860 | -35.1162 | drawdown |
| historical | assumed_1/offer_value | 15 bp | 148.3452 | 25.5111 | -35.1398 | drawdown |
| historical | assumed_1/offer_value | 30 bp | 137.3386 | 19.5816 | -35.1162 | drawdown |
| historical | assumed_5/offer_value | 15 bp | 148.3452 | 25.5111 | -35.1398 | drawdown |
| historical | assumed_5/offer_value | 30 bp | 137.3386 | 19.5816 | -35.1162 | drawdown |
| historical | assumed_20/offer_value | 15 bp | 149.7898 | 26.7342 | -34.6088 | drawdown |
| historical | assumed_20/offer_value | 30 bp | 138.9241 | 21.6293 | -34.4720 | drawdown |
| extension | locked/offer_value | 15 bp | 137.9345 | 37.3148 | -31.2368 | drawdown |
| extension | locked/offer_value | 30 bp | 126.8410 | 32.1977 | -31.9701 | drawdown |
| extension | assumed_0/offer_value | 15 bp | 129.4756 | 15.5524 | -36.2617 | drawdown |
| extension | assumed_0/offer_value | 30 bp | 118.4566 | 10.3737 | -36.6807 | drawdown |
| extension | assumed_1/offer_value | 15 bp | 129.4756 | 15.6025 | -36.2617 | drawdown |
| extension | assumed_1/offer_value | 30 bp | 118.4566 | 10.2767 | -36.6807 | drawdown |
| extension | assumed_5/offer_value | 15 bp | 129.4756 | 15.6025 | -36.2617 | drawdown |
| extension | assumed_5/offer_value | 30 bp | 118.4566 | 10.2767 | -36.6807 | drawdown |
| extension | assumed_20/offer_value | 15 bp | 130.6733 | 16.3911 | -35.7838 | drawdown |
| extension | assumed_20/offer_value | 30 bp | 119.9375 | 11.9779 | -36.0989 | drawdown |

The historical boundary is 2026-09-01; extended rows retain the same account through 2026-10-28.
Later-segment metrics are preserved separately in the JSON; neither segment is an untouched holdout.
All five payment policies and both costs are retained. Assumed merger payment dates are unverified.
Independent ranking/timing and accounting checks validate implementation, not independent market evidence.
Vendor backfill, unverified payment dates, opening liquidity and actual execution costs remain limitations.
The five existing gates and original Core paper identity are unchanged. No parameter is selected after results.


## Fixed display case: assumed 5-session payment, 15 bp/side, last-quote halt mark

| Account | Net % | Daily drawdown % | Daily Sharpe, RF=0 | Actual fees USD |
|---|---:|---:|---:|---:|
| momentum-core-formation-normalized-research-v1 | 129.4756 | -36.2617 | 0.9204382393103705 | 9014.98 |
| Core control | 15.6025 | -47.3774 | 0.34667256037429345 | 5701.84 |
| SPY | 68.0753 | -18.4922 | 1.2933827496517174 | 149.60 |
| Prior 63-return normalization | 62.4793 | -20.9409 | 0.8428696398097738 | 6550.67 |

| Calendar period | Normalized % | Core % | SPY % | Normalized drawdown % | Normalized Sharpe |
|---|---:|---:|---:|---:|---:|
| 2024 | 57.0238 | 8.8957 | 25.8660 | -18.8979 | 1.4751476899931932 |
| 2025 | -1.9684 | -12.4374 | 17.3690 | -30.0389 | 0.1398930692649139 |
| 2026 | 49.0751 | 21.2377 | 13.7737 | -36.2617 | 1.2022728835096068 |

The display case is not a selected approval scenario: all 40 marking/payment/cost/phase results remain above and in JSON.
No fresh out-of-sample history exists in these previously reviewed inputs. The later segment is reported separately, without relabelling it.
