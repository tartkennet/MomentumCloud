# Momentum10 v2 — completed retention and stop research

**Status: NO_GO**. Prospective paper started: false. Broker orders/live approved: false.

Original frozen protocol/source: `f156b4175ad59a119b6f0e7071c90e928366637b`. Executed source: `d0eb0f3d84a0636c7ca50f12a96f61105aaef07c`.
[Complete evidence run 41185508350](https://github.com/tartkennet/MomentumCloud/actions/runs/41185508350); immutable draft release `m10v2-research-41185508350-1`.
Artifact ZIP SHA256 `1f62dff477650922b3c4b959a006036b39316d2b593774357cd3c620d0ab2ed3`. Saved inputs and original ECB fixing reused offline.
All results are reused DEVELOPMENT history, not untouched OOS. H3 and Stocks10 A/B unchanged.
Completed M1/M2 states from the first run are reused with new full independent reconciliation; native-currency payments must be zero and financial metrics identical. Native TD repair and its independent audit apply only to the new study.

| Main case | Net USD % | DD USD % | Sharpe | Fees USD | Orders | Gross turnover / avg NAV / year % | Net SEK % | DD SEK % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | 43.59 | -36.41 | 0.52 | 841.08 | 433 | 1317.23 | 42.09 | -40.21 |
| M2 | 36.10 | -39.44 | 0.47 | 535.88 | 288 | 822.31 | 34.68 | -47.94 |
| M3 | 19.83 | -52.65 | 0.36 | 416.37 | 217 | 642.23 | 18.58 | -58.92 |
| Q10 | 34.08 | -29.83 | 0.48 | 435.63 | 226 | 687.28 | 32.68 | -40.42 |
| QV | 18.14 | -52.20 | 0.35 | 419.46 | 217 | 643.45 | 16.91 | -58.53 |
| C | 13.88 | -18.68 | 0.54 | 49.92 | 40 | 38.72 | 12.69 | -34.37 |

Main case = 5-session assumed merger payment, last observed confirmed-halt mark, 15bp execution reserve PLUS max(1USD,.25%) commission and .25% FX reserve. Stress uses 30bp execution reserve. Gross turnover counts buys+sells, including initial purchases; one-way is half.

## All financial and operational decisions

| Variant | Financial pass / 20 | Paper pass / 20 | Failed financial gates (scenario counts) | Operational reasons |
|---|---:|---:|---|---|
| M1 | 0 | 0 | {'beats_spy': 20, 'drawdown': 20} | {'EXTRA_OR_SUBWHOLE_EQUITY_ENTITLEMENT': 3080} |
| M2 | 0 | 0 | {'beats_spy': 20, 'drawdown': 20} | {'EXTRA_OR_SUBWHOLE_EQUITY_ENTITLEMENT': 3080} |
| M3 | 0 | 0 | {'beats_spy': 20, 'drawdown': 20} | {} |
| Q10 | 0 | 0 | {'beats_spy': 20, 'drawdown': 20} | {} |
| QV | 0 | 0 | {'beats_spy': 20, 'drawdown': 20} | {'INEFFECTIVE_NONPOSITIVE_STOP': 60} |
| C | 0 | 0 | {'beats_spy': 20, 'hit_rate': 20} | {'MINIMUM_COMPLETE_BASKET_UNFUNDED': 220} |

## Comparison without rerunning completed experiments

| Saved model | Net USD % | DD USD % | Sharpe | Fees USD | Gross notional / initial capital / year % |
|---|---:|---:|---:|---:|---:|
| Stocks10 A | 6.39 | -45.03 | 0.27 | 722.84 | 1284.19 |
| Stocks10 B | 35.44 | -29.80 | 0.47 | 885.30 | 1783.66 |
| H3 (100k USD, different 15bp fees) | 77.13 | -16.08 | 1.307248900169288 | 3122.86 | 741.02 |
| Core (100k USD, different 15bp fees) | 15.60 | -47.38 | 0.34667256037429345 | 5701.84 | 1352.98 |

Same-small-account SPY total return: 64.02% USD; DD -17.81%; Sharpe 1.28; fees 12.23 USD. It is only a comparator, never a Momentum10 asset.
H3/Core turnover is inferred from their verified proportional fee function and reported on INITIAL capital, not average NAV. This preserves honest comparability of definitions; retail fees differ.

## Interpretation, recovery and limitations

C is INFEASIBLE at the declared risk budget: its low trading cost and lower drawdown must be read together with eleven blocked complete baskets in the main case. It cannot be presented as a successful risk solution. QV has three entries whose prescribed stop distance is at least 100%, giving no positive stop barrier; these fail operational admission.

The PRESELECTED quarterly retention case M3 pays 416.37 USD versus B's 885.30, with 217 market orders versus B's 486. Its net-return difference is -15.61 percentage points; DD difference is -22.85 points. Do not select frequency by the largest historical return.
M1/M2/M3 isolate selection frequency while retaining quantities. Q10/QV compare close-stop principles at the prechosen quarter. Same-close stops create cash slots, not immediate replacement or repurchase. C, if present, is the preregistered next portfolio-exposure hypothesis, not an optimized extra stop setting.

* M1: worst episode {'peak': '2026-05-26', 'trough': '2026-10-16', 'drawdown_pct': -36.40519829289074, 'recovered': None}. Individual stop fills 0; 0 below the then-current barrier. 21 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon; 63 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon.
* M2: worst episode {'peak': '2024-11-11', 'trough': '2025-08-19', 'drawdown_pct': -39.43946530681406, 'recovered': '2026-02-24'}. Individual stop fills 0; 0 below the then-current barrier. 21 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon; 63 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon.
* M3: worst episode {'peak': '2025-02-18', 'trough': '2025-12-17', 'drawdown_pct': -52.65252342465412, 'recovered': None}. Individual stop fills 0; 0 below the then-current barrier. 21 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon; 63 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon.
* Q10: worst episode {'peak': '2024-11-29', 'trough': '2025-12-17', 'drawdown_pct': -29.82682919388249, 'recovered': '2026-03-02'}. Individual stop fills 56; 48 below the then-current barrier. 21 sessions: 52 comparable, 30 end above exit price, 23 regain entry within horizon; 63 sessions: 50 comparable, 18 end above exit price, 29 regain entry within horizon.
* QV: worst episode {'peak': '2025-02-18', 'trough': '2025-12-17', 'drawdown_pct': -52.20337039221478, 'recovered': None}. Individual stop fills 6; 6 below the then-current barrier. 21 sessions: 5 comparable, 0 end above exit price, 0 regain entry within horizon; 63 sessions: 4 comparable, 2 end above exit price, 0 regain entry within horizon.
* C: worst episode {'peak': '2024-12-04', 'trough': '2026-01-05', 'drawdown_pct': -18.679187183910816, 'recovered': None}. Individual stop fills 0; 0 below the then-current barrier. 21 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon; 63 sessions: 0 comparable, 0 end above exit price, 0 regain entry within horizon.

Post-stop returns are price-only, split-neutral DESCRIPTIVE shadows; no future quote feeds a decision, no dividends/costs are credited, incomplete/delisted windows stay missing.
All cash/claims/corporate events and NAV, full eligible ranks, retention, calendar, stop basis/blacklist/timing, actual opening prices and financial measures are independently reconciled. Same vendor, not independent vendor confirmation.
Paper candidate under the frozen priority: None. Financial candidate before operational screens: None. If none is admitted, no new prospective account is created and no past trade is relabelled as new paper evidence.
Operational reason counts are daily observations, not counts of independent incidents. Native dividend claims stay in their declared currency until payment, are marked with prior-date ECB crosses, and incur the disclosed conversion reserve; no actual bank FX rate is invented.
Extra/subwhole corporate entitlements and missing quotes remain visible and fail operational admission. Low cost alone is not a financial GO. Closing-price stop tests cannot establish intraday broker-stop performance or guarantee a maximum future loss.
No gate, interval anchor, stop multiplier, reference-price rule or ranking parameter was tuned after results. If the one conditional risk-budget case also fails, its failure remains part of the register; do not silently invent a seventh variant.
