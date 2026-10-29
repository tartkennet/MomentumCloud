# Core risk-normalized ranking — 29 October 2026

All observations are previously inspected development history. No live approval.

Study fingerprint: `657bbcfd4debd1f400ea5e7fb45e2914601b2f1bd4135556259d46f0d2c3f597`.

| Phase | Payment policy | Cost/side | Candidate net % | Baseline net % | Candidate drawdown % | Failed gates |
|---|---|---:|---:|---:|---:|---|
| historical | locked/last_quote | 15 bp | 89.6505 | 44.3054 | -20.7814 | drawdown |
| historical | locked/last_quote | 30 bp | 86.8174 | 39.5403 | -20.9370 | drawdown |
| historical | assumed_0/last_quote | 15 bp | 90.8478 | 25.4550 | -21.1394 | drawdown |
| historical | assumed_0/last_quote | 30 bp | 87.9319 | 19.6860 | -21.2792 | drawdown |
| historical | assumed_1/last_quote | 15 bp | 90.8478 | 25.5111 | -21.1394 | drawdown |
| historical | assumed_1/last_quote | 30 bp | 87.9319 | 19.5816 | -21.2792 | drawdown |
| historical | assumed_5/last_quote | 15 bp | 90.8478 | 25.5111 | -21.1394 | drawdown |
| historical | assumed_5/last_quote | 30 bp | 87.9319 | 19.5816 | -21.2792 | drawdown |
| historical | assumed_20/last_quote | 15 bp | 90.8465 | 26.7342 | -21.1420 | drawdown |
| historical | assumed_20/last_quote | 30 bp | 87.9784 | 21.6293 | -21.2799 | drawdown |
| extension | locked/last_quote | 15 bp | 89.7528 | 37.3148 | -20.7814 | drawdown |
| extension | locked/last_quote | 30 bp | 86.7480 | 32.1977 | -20.9370 | drawdown |
| extension | assumed_0/last_quote | 15 bp | 90.6256 | 15.5524 | -21.1394 | drawdown |
| extension | assumed_0/last_quote | 30 bp | 87.3900 | 10.3737 | -21.2792 | drawdown |
| extension | assumed_1/last_quote | 15 bp | 90.6256 | 15.6025 | -21.1394 | drawdown |
| extension | assumed_1/last_quote | 30 bp | 87.3900 | 10.2767 | -21.2792 | drawdown |
| extension | assumed_5/last_quote | 15 bp | 90.6256 | 15.6025 | -21.1394 | drawdown |
| extension | assumed_5/last_quote | 30 bp | 87.3900 | 10.2767 | -21.2792 | drawdown |
| extension | assumed_20/last_quote | 15 bp | 90.6242 | 16.3911 | -21.1420 | drawdown |
| extension | assumed_20/last_quote | 30 bp | 87.4360 | 11.9779 | -21.2799 | drawdown |
| historical | locked/offer_value | 15 bp | 89.6505 | 44.3054 | -20.7814 | drawdown |
| historical | locked/offer_value | 30 bp | 86.8174 | 39.5403 | -20.9370 | drawdown |
| historical | assumed_0/offer_value | 15 bp | 90.8478 | 25.4550 | -21.1394 | drawdown |
| historical | assumed_0/offer_value | 30 bp | 87.9319 | 19.6860 | -21.2792 | drawdown |
| historical | assumed_1/offer_value | 15 bp | 90.8478 | 25.5111 | -21.1394 | drawdown |
| historical | assumed_1/offer_value | 30 bp | 87.9319 | 19.5816 | -21.2792 | drawdown |
| historical | assumed_5/offer_value | 15 bp | 90.8478 | 25.5111 | -21.1394 | drawdown |
| historical | assumed_5/offer_value | 30 bp | 87.9319 | 19.5816 | -21.2792 | drawdown |
| historical | assumed_20/offer_value | 15 bp | 90.8465 | 26.7342 | -21.1420 | drawdown |
| historical | assumed_20/offer_value | 30 bp | 87.9784 | 21.6293 | -21.2799 | drawdown |
| extension | locked/offer_value | 15 bp | 89.7528 | 37.3148 | -20.7814 | drawdown |
| extension | locked/offer_value | 30 bp | 86.7480 | 32.1977 | -20.9370 | drawdown |
| extension | assumed_0/offer_value | 15 bp | 90.6256 | 15.5524 | -21.1394 | drawdown |
| extension | assumed_0/offer_value | 30 bp | 87.3900 | 10.3737 | -21.2792 | drawdown |
| extension | assumed_1/offer_value | 15 bp | 90.6256 | 15.6025 | -21.1394 | drawdown |
| extension | assumed_1/offer_value | 30 bp | 87.3900 | 10.2767 | -21.2792 | drawdown |
| extension | assumed_5/offer_value | 15 bp | 90.6256 | 15.6025 | -21.1394 | drawdown |
| extension | assumed_5/offer_value | 30 bp | 87.3900 | 10.2767 | -21.2792 | drawdown |
| extension | assumed_20/offer_value | 15 bp | 90.6242 | 16.3911 | -21.1420 | drawdown |
| extension | assumed_20/offer_value | 30 bp | 87.4360 | 11.9779 | -21.2799 | drawdown |

The historical boundary is 2026-09-01; extended rows retain the same account through 2026-10-28.
Later-segment metrics are preserved separately in the JSON; neither segment is an untouched holdout.
All five payment policies and both costs are retained. Assumed merger payment dates are unverified.
Independent ranking/timing and accounting checks validate implementation, not independent market evidence.
Vendor backfill, unverified payment dates, opening liquidity and actual execution costs remain limitations.
The five existing gates and original Core paper identity are unchanged. No parameter is selected after results.


## Fixed display case: assumed 5-session payment, 15 bp/side, last-quote halt mark

| Account | Net % | Daily drawdown % | Daily Sharpe, RF=0 | Actual fees USD |
|---|---:|---:|---:|---:|
| momentum-diversified-core-research-v1 | 90.6256 | -21.1394 | 1.3709906688249442 | 2391.78 |
| Core control | 15.6025 | -47.3774 | 0.34667256037429345 | 5701.84 |
| SPY | 68.0753 | -18.4922 | 1.2933827496517174 | 149.60 |
| Prior 63-return normalization | 62.4793 | -20.9409 | 0.8428696398097738 | 6550.67 |

| Calendar period | Normalized % | Core % | SPY % | Normalized drawdown % | Normalized Sharpe |
|---|---:|---:|---:|---:|---:|
| 2024 | 36.4666 | 8.8957 | 25.8660 | -10.2849 | 1.8914952018312339 |
| 2025 | 11.8736 | -12.4374 | 17.3690 | -21.1394 | 0.6922541964646813 |
| 2026 | 24.8611 | 21.2377 | 13.7737 | -9.1014 | 1.6322576679628675 |

The display case is not a selected approval scenario: all 40 marking/payment/cost/phase results remain above and in JSON.
No fresh out-of-sample history exists in these previously reviewed inputs. The later segment is reported separately, without relabelling it.

## Completed PR23 comparator, identical assumptions

| Phase | Policy/mark | Cost bp | PR23 net % | PR23 DD % | New net % | New DD % | H1 net % | H1 DD % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| historical | locked/last_quote | 15 | 150.6381 | -31.2368 | 89.6505 | -20.7814 | 54.3054 | -14.1812 |
| historical | locked/last_quote | 30 | 139.4809 | -31.9701 | 86.8174 | -20.9370 | 51.6248 | -14.6501 |
| historical | assumed_0/last_quote | 15 | 148.3452 | -35.1398 | 90.8478 | -21.1394 | 54.3054 | -14.1812 |
| historical | assumed_0/last_quote | 30 | 137.3386 | -35.1162 | 87.9319 | -21.2792 | 51.6248 | -14.6501 |
| historical | assumed_1/last_quote | 15 | 148.3452 | -35.1398 | 90.8478 | -21.1394 | 54.3054 | -14.1812 |
| historical | assumed_1/last_quote | 30 | 137.3386 | -35.1162 | 87.9319 | -21.2792 | 51.6248 | -14.6501 |
| historical | assumed_5/last_quote | 15 | 148.3452 | -35.1398 | 90.8478 | -21.1394 | 54.3054 | -14.1812 |
| historical | assumed_5/last_quote | 30 | 137.3386 | -35.1162 | 87.9319 | -21.2792 | 51.6248 | -14.6501 |
| historical | assumed_20/last_quote | 15 | 149.7898 | -34.6088 | 90.8465 | -21.1420 | 54.3054 | -14.1812 |
| historical | assumed_20/last_quote | 30 | 138.9241 | -34.4720 | 87.9784 | -21.2799 | 51.6248 | -14.6501 |
| extension | locked/last_quote | 15 | 137.9345 | -31.2368 | 89.7528 | -20.7814 | 51.5508 | -14.1812 |
| extension | locked/last_quote | 30 | 126.8410 | -31.9701 | 86.7480 | -20.9370 | 48.8586 | -14.6501 |
| extension | assumed_0/last_quote | 15 | 129.4756 | -36.2617 | 90.6256 | -21.1394 | 51.5508 | -14.1812 |
| extension | assumed_0/last_quote | 30 | 118.4566 | -36.6807 | 87.3900 | -21.2792 | 48.8586 | -14.6501 |
| extension | assumed_1/last_quote | 15 | 129.4756 | -36.2617 | 90.6256 | -21.1394 | 51.5508 | -14.1812 |
| extension | assumed_1/last_quote | 30 | 118.4566 | -36.6807 | 87.3900 | -21.2792 | 48.8586 | -14.6501 |
| extension | assumed_5/last_quote | 15 | 129.4756 | -36.2617 | 90.6256 | -21.1394 | 51.5508 | -14.1812 |
| extension | assumed_5/last_quote | 30 | 118.4566 | -36.6807 | 87.3900 | -21.2792 | 48.8586 | -14.6501 |
| extension | assumed_20/last_quote | 15 | 130.6733 | -35.7838 | 90.6242 | -21.1420 | 51.5508 | -14.1812 |
| extension | assumed_20/last_quote | 30 | 119.9375 | -36.0989 | 87.4360 | -21.2799 | 48.8586 | -14.6501 |
| historical | locked/offer_value | 15 | 150.6381 | -31.2368 | 89.6505 | -20.7814 | 54.3054 | -14.1812 |
| historical | locked/offer_value | 30 | 139.4809 | -31.9701 | 86.8174 | -20.9370 | 51.6248 | -14.6501 |
| historical | assumed_0/offer_value | 15 | 148.3452 | -35.1398 | 90.8478 | -21.1394 | 54.3054 | -14.1812 |
| historical | assumed_0/offer_value | 30 | 137.3386 | -35.1162 | 87.9319 | -21.2792 | 51.6248 | -14.6501 |
| historical | assumed_1/offer_value | 15 | 148.3452 | -35.1398 | 90.8478 | -21.1394 | 54.3054 | -14.1812 |
| historical | assumed_1/offer_value | 30 | 137.3386 | -35.1162 | 87.9319 | -21.2792 | 51.6248 | -14.6501 |
| historical | assumed_5/offer_value | 15 | 148.3452 | -35.1398 | 90.8478 | -21.1394 | 54.3054 | -14.1812 |
| historical | assumed_5/offer_value | 30 | 137.3386 | -35.1162 | 87.9319 | -21.2792 | 51.6248 | -14.6501 |
| historical | assumed_20/offer_value | 15 | 149.7898 | -34.6088 | 90.8465 | -21.1420 | 54.3054 | -14.1812 |
| historical | assumed_20/offer_value | 30 | 138.9241 | -34.4720 | 87.9784 | -21.2799 | 51.6248 | -14.6501 |
| extension | locked/offer_value | 15 | 137.9345 | -31.2368 | 89.7528 | -20.7814 | 51.5508 | -14.1812 |
| extension | locked/offer_value | 30 | 126.8410 | -31.9701 | 86.7480 | -20.9370 | 48.8586 | -14.6501 |
| extension | assumed_0/offer_value | 15 | 129.4756 | -36.2617 | 90.6256 | -21.1394 | 51.5508 | -14.1812 |
| extension | assumed_0/offer_value | 30 | 118.4566 | -36.6807 | 87.3900 | -21.2792 | 48.8586 | -14.6501 |
| extension | assumed_1/offer_value | 15 | 129.4756 | -36.2617 | 90.6256 | -21.1394 | 51.5508 | -14.1812 |
| extension | assumed_1/offer_value | 30 | 118.4566 | -36.6807 | 87.3900 | -21.2792 | 48.8586 | -14.6501 |
| extension | assumed_5/offer_value | 15 | 129.4756 | -36.2617 | 90.6256 | -21.1394 | 51.5508 | -14.1812 |
| extension | assumed_5/offer_value | 30 | 118.4566 | -36.6807 | 87.3900 | -21.2792 | 48.8586 | -14.6501 |
| extension | assumed_20/offer_value | 15 | 130.6733 | -35.7838 | 90.6242 | -21.1420 | 51.5508 | -14.1812 |
| extension | assumed_20/offer_value | 30 | 119.9375 | -36.0989 | 87.4360 | -21.2799 | 48.8586 | -14.6501 |
