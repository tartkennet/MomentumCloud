# Core risk-normalized ranking — 29 October 2026

All observations are previously inspected development history. No live approval.

Study fingerprint: `8b29f98a971446b0ce0f50beb637d4ab18481c6acc0b7c71c0e5daf0a6e3d222`.

| Phase | Payment policy | Cost/side | Candidate net % | Baseline net % | Candidate drawdown % | Failed gates |
|---|---|---:|---:|---:|---:|---|
| historical | locked/last_quote | 15 bp | 54.3054 | 44.3054 | -14.1812 | beats_spy |
| historical | locked/last_quote | 30 bp | 51.6248 | 39.5403 | -14.6501 | beats_spy |
| historical | assumed_0/last_quote | 15 bp | 54.3054 | 25.4550 | -14.1812 | beats_spy |
| historical | assumed_0/last_quote | 30 bp | 51.6248 | 19.6860 | -14.6501 | beats_spy |
| historical | assumed_1/last_quote | 15 bp | 54.3054 | 25.5111 | -14.1812 | beats_spy |
| historical | assumed_1/last_quote | 30 bp | 51.6248 | 19.5816 | -14.6501 | beats_spy |
| historical | assumed_5/last_quote | 15 bp | 54.3054 | 25.5111 | -14.1812 | beats_spy |
| historical | assumed_5/last_quote | 30 bp | 51.6248 | 19.5816 | -14.6501 | beats_spy |
| historical | assumed_20/last_quote | 15 bp | 54.3054 | 26.7342 | -14.1812 | beats_spy |
| historical | assumed_20/last_quote | 30 bp | 51.6248 | 21.6293 | -14.6501 | beats_spy |
| extension | locked/last_quote | 15 bp | 51.5508 | 37.3148 | -14.1812 | beats_spy |
| extension | locked/last_quote | 30 bp | 48.8586 | 32.1977 | -14.6501 | beats_spy |
| extension | assumed_0/last_quote | 15 bp | 51.5508 | 15.5524 | -14.1812 | beats_spy |
| extension | assumed_0/last_quote | 30 bp | 48.8586 | 10.3737 | -14.6501 | beats_spy |
| extension | assumed_1/last_quote | 15 bp | 51.5508 | 15.6025 | -14.1812 | beats_spy |
| extension | assumed_1/last_quote | 30 bp | 48.8586 | 10.2767 | -14.6501 | beats_spy |
| extension | assumed_5/last_quote | 15 bp | 51.5508 | 15.6025 | -14.1812 | beats_spy |
| extension | assumed_5/last_quote | 30 bp | 48.8586 | 10.2767 | -14.6501 | beats_spy |
| extension | assumed_20/last_quote | 15 bp | 51.5508 | 16.3911 | -14.1812 | beats_spy |
| extension | assumed_20/last_quote | 30 bp | 48.8586 | 11.9779 | -14.6501 | beats_spy |
| historical | locked/offer_value | 15 bp | 54.3054 | 44.3054 | -14.1812 | beats_spy |
| historical | locked/offer_value | 30 bp | 51.6248 | 39.5403 | -14.6501 | beats_spy |
| historical | assumed_0/offer_value | 15 bp | 54.3054 | 25.4550 | -14.1812 | beats_spy |
| historical | assumed_0/offer_value | 30 bp | 51.6248 | 19.6860 | -14.6501 | beats_spy |
| historical | assumed_1/offer_value | 15 bp | 54.3054 | 25.5111 | -14.1812 | beats_spy |
| historical | assumed_1/offer_value | 30 bp | 51.6248 | 19.5816 | -14.6501 | beats_spy |
| historical | assumed_5/offer_value | 15 bp | 54.3054 | 25.5111 | -14.1812 | beats_spy |
| historical | assumed_5/offer_value | 30 bp | 51.6248 | 19.5816 | -14.6501 | beats_spy |
| historical | assumed_20/offer_value | 15 bp | 54.3054 | 26.7342 | -14.1812 | beats_spy |
| historical | assumed_20/offer_value | 30 bp | 51.6248 | 21.6293 | -14.6501 | beats_spy |
| extension | locked/offer_value | 15 bp | 51.5508 | 37.3148 | -14.1812 | beats_spy |
| extension | locked/offer_value | 30 bp | 48.8586 | 32.1977 | -14.6501 | beats_spy |
| extension | assumed_0/offer_value | 15 bp | 51.5508 | 15.5524 | -14.1812 | beats_spy |
| extension | assumed_0/offer_value | 30 bp | 48.8586 | 10.3737 | -14.6501 | beats_spy |
| extension | assumed_1/offer_value | 15 bp | 51.5508 | 15.6025 | -14.1812 | beats_spy |
| extension | assumed_1/offer_value | 30 bp | 48.8586 | 10.2767 | -14.6501 | beats_spy |
| extension | assumed_5/offer_value | 15 bp | 51.5508 | 15.6025 | -14.1812 | beats_spy |
| extension | assumed_5/offer_value | 30 bp | 48.8586 | 10.2767 | -14.6501 | beats_spy |
| extension | assumed_20/offer_value | 15 bp | 51.5508 | 16.3911 | -14.1812 | beats_spy |
| extension | assumed_20/offer_value | 30 bp | 48.8586 | 11.9779 | -14.6501 | beats_spy |

The historical boundary is 2026-09-01; extended rows retain the same account through 2026-10-28.
Later-segment metrics are preserved separately in the JSON; neither segment is an untouched holdout.
All five payment policies and both costs are retained. Assumed merger payment dates are unverified.
Independent ranking/timing and accounting checks validate implementation, not independent market evidence.
Vendor backfill, unverified payment dates, opening liquidity and actual execution costs remain limitations.
The five existing gates and original Core paper identity are unchanged. No parameter is selected after results.


## Fixed display case: assumed 5-session payment, 15 bp/side, last-quote halt mark

| Account | Net % | Daily drawdown % | Daily Sharpe, RF=0 | Actual fees USD |
|---|---:|---:|---:|---:|
| momentum-portfolio-benchmark-risk-research-v1 | 51.5508 | -14.1812 | 1.1480398847688036 | 2639.02 |
| Core control | 15.6025 | -47.3774 | 0.34667256037429345 | 5701.84 |
| SPY | 68.0753 | -18.4922 | 1.2933827496517174 | 149.60 |
| Prior 63-return normalization | 62.4793 | -20.9409 | 0.8428696398097738 | 6550.67 |

| Calendar period | Normalized % | Core % | SPY % | Normalized drawdown % | Normalized Sharpe |
|---|---:|---:|---:|---:|---:|
| 2024 | 27.6502 | 8.8957 | 25.8660 | -7.0079 | 1.8318478826880125 |
| 2025 | 1.0317 | -12.4374 | 17.3690 | -13.1918 | 0.14374197038072525 |
| 2026 | 17.5111 | 21.2377 | 13.7737 | -9.1103 | 1.5597398712011716 |

The display case is not a selected approval scenario: all 40 marking/payment/cost/phase results remain above and in JSON.
No fresh out-of-sample history exists in these previously reviewed inputs. The later segment is reported separately, without relabelling it.

## Completed PR23 comparator, identical assumptions

| Phase | Policy/mark | Cost bp | PR23 net % | PR23 DD % | New net % | New DD % |
|---|---|---:|---:|---:|---:|---:|
| historical | locked/last_quote | 15 | 150.6381 | -31.2368 | 54.3054 | -14.1812 |
| historical | locked/last_quote | 30 | 139.4809 | -31.9701 | 51.6248 | -14.6501 |
| historical | assumed_0/last_quote | 15 | 148.3452 | -35.1398 | 54.3054 | -14.1812 |
| historical | assumed_0/last_quote | 30 | 137.3386 | -35.1162 | 51.6248 | -14.6501 |
| historical | assumed_1/last_quote | 15 | 148.3452 | -35.1398 | 54.3054 | -14.1812 |
| historical | assumed_1/last_quote | 30 | 137.3386 | -35.1162 | 51.6248 | -14.6501 |
| historical | assumed_5/last_quote | 15 | 148.3452 | -35.1398 | 54.3054 | -14.1812 |
| historical | assumed_5/last_quote | 30 | 137.3386 | -35.1162 | 51.6248 | -14.6501 |
| historical | assumed_20/last_quote | 15 | 149.7898 | -34.6088 | 54.3054 | -14.1812 |
| historical | assumed_20/last_quote | 30 | 138.9241 | -34.4720 | 51.6248 | -14.6501 |
| extension | locked/last_quote | 15 | 137.9345 | -31.2368 | 51.5508 | -14.1812 |
| extension | locked/last_quote | 30 | 126.8410 | -31.9701 | 48.8586 | -14.6501 |
| extension | assumed_0/last_quote | 15 | 129.4756 | -36.2617 | 51.5508 | -14.1812 |
| extension | assumed_0/last_quote | 30 | 118.4566 | -36.6807 | 48.8586 | -14.6501 |
| extension | assumed_1/last_quote | 15 | 129.4756 | -36.2617 | 51.5508 | -14.1812 |
| extension | assumed_1/last_quote | 30 | 118.4566 | -36.6807 | 48.8586 | -14.6501 |
| extension | assumed_5/last_quote | 15 | 129.4756 | -36.2617 | 51.5508 | -14.1812 |
| extension | assumed_5/last_quote | 30 | 118.4566 | -36.6807 | 48.8586 | -14.6501 |
| extension | assumed_20/last_quote | 15 | 130.6733 | -35.7838 | 51.5508 | -14.1812 |
| extension | assumed_20/last_quote | 30 | 119.9375 | -36.0989 | 48.8586 | -14.6501 |
| historical | locked/offer_value | 15 | 150.6381 | -31.2368 | 54.3054 | -14.1812 |
| historical | locked/offer_value | 30 | 139.4809 | -31.9701 | 51.6248 | -14.6501 |
| historical | assumed_0/offer_value | 15 | 148.3452 | -35.1398 | 54.3054 | -14.1812 |
| historical | assumed_0/offer_value | 30 | 137.3386 | -35.1162 | 51.6248 | -14.6501 |
| historical | assumed_1/offer_value | 15 | 148.3452 | -35.1398 | 54.3054 | -14.1812 |
| historical | assumed_1/offer_value | 30 | 137.3386 | -35.1162 | 51.6248 | -14.6501 |
| historical | assumed_5/offer_value | 15 | 148.3452 | -35.1398 | 54.3054 | -14.1812 |
| historical | assumed_5/offer_value | 30 | 137.3386 | -35.1162 | 51.6248 | -14.6501 |
| historical | assumed_20/offer_value | 15 | 149.7898 | -34.6088 | 54.3054 | -14.1812 |
| historical | assumed_20/offer_value | 30 | 138.9241 | -34.4720 | 51.6248 | -14.6501 |
| extension | locked/offer_value | 15 | 137.9345 | -31.2368 | 51.5508 | -14.1812 |
| extension | locked/offer_value | 30 | 126.8410 | -31.9701 | 48.8586 | -14.6501 |
| extension | assumed_0/offer_value | 15 | 129.4756 | -36.2617 | 51.5508 | -14.1812 |
| extension | assumed_0/offer_value | 30 | 118.4566 | -36.6807 | 48.8586 | -14.6501 |
| extension | assumed_1/offer_value | 15 | 129.4756 | -36.2617 | 51.5508 | -14.1812 |
| extension | assumed_1/offer_value | 30 | 118.4566 | -36.6807 | 48.8586 | -14.6501 |
| extension | assumed_5/offer_value | 15 | 129.4756 | -36.2617 | 51.5508 | -14.1812 |
| extension | assumed_5/offer_value | 30 | 118.4566 | -36.6807 | 48.8586 | -14.6501 |
| extension | assumed_20/offer_value | 15 | 130.6733 | -35.7838 | 51.5508 | -14.1812 |
| extension | assumed_20/offer_value | 30 | 119.9375 | -36.0989 | 48.8586 | -14.6501 |
