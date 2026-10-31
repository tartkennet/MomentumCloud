# Momentum 10 v3 — complete issue #33 research results

Status: **NO_GO**. 220 completed scenarios. Source `5c16eb204083112c27c0bf323fb96c6867cca80c`; [run](https://github.com/tartkennet/MomentumCloud/actions/runs/41198217897).

Reviewed historical DEVELOPMENT data, not untouched OOS. Frozen hypothesis order: R, T, D. No source/parameter/gate tuning after outcomes.

| Attempt | Net USD % | DD % | Sharpe | Fees USD | Orders | Gross turnover / mean NAV / year % | Net SEK % | DD SEK % | Financial /20 | Paper /20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R_M1_none | -16.84 | -56.64 | 0.07 | 811.27 | 489 | 1430.71 | -17.71 | -62.69 | 0 | 0 |
| T_M1_none | -21.26 | -56.84 | 0.03 | 798.60 | 485 | 1416.47 | -22.08 | -62.90 | 0 | 0 |
| D_M1_none | -19.63 | -56.84 | 0.04 | 798.63 | 485 | 1413.84 | -20.47 | -62.90 | 0 | 0 |
| D_M2_none | -53.86 | -69.83 | -0.42 | 490.57 | 306 | 923.09 | -54.34 | -72.62 | 0 | 0 |
| D_M3_none | -4.90 | -55.53 | 0.17 | 389.15 | 233 | 685.99 | -5.90 | -60.49 | 0 | 0 |
| D_M1_fixed10 | -33.86 | -53.46 | -0.24 | 803.41 | 512 | 1515.81 | -34.55 | -60.04 | 0 | 0 |
| D_M2_fixed10 | -26.70 | -48.15 | -0.24 | 519.86 | 316 | 962.21 | -27.46 | -56.54 | 0 | 0 |
| D_M3_fixed10 | 11.21 | -31.63 | 0.28 | 444.40 | 246 | 769.70 | 10.05 | -40.80 | 0 | 0 |
| D_M1_vol | -19.87 | -56.76 | 0.04 | 799.36 | 485 | 1416.27 | -20.71 | -62.86 | 0 | 0 |
| D_M2_vol | -48.89 | -65.85 | -0.35 | 493.43 | 307 | 920.82 | -49.42 | -68.98 | 0 | 0 |
| D_M3_vol | -2.63 | -54.57 | 0.19 | 390.46 | 233 | 683.06 | -3.64 | -59.65 | 0 | 0 |

Bounded run 41196824070 preserved 183 independently approved cases; this run completed only the other 37. Frozen strategy/auditor/input hashes and recomputed metrics/gates match reused cases. No approved strategy experiment was repeated.

Main case: assumed payment after five sessions, confirmed-halt last quote, 15bp execution reserve PLUS max(1USD,.25%) commission and .25% FX reserve. Stress execution30bp. Whole-share cash accounts start SEK20,000 with the same strictly prior-date ECB input. Gross turnover is buys+sells including initial purchases; one-way is half.

## Failed gates and operational constraints

* R_M1_none: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20}.
* T_M1_none: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20}.
* D_M1_none: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20}.
* D_M2_none: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20, 'hit_rate': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20}.
* D_M3_none: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20}; operational observations {}.
* D_M1_fixed10: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20, 'hit_rate': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20}.
* D_M2_fixed10: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20, 'hit_rate': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20}.
* D_M3_fixed10: financial failures {'beats_spy': 20, 'drawdown': 20, 'hit_rate': 20}; operational observations {}.
* D_M1_vol: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20, 'INEFFECTIVE_NONPOSITIVE_STOP': 380}.
* D_M2_vol: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20, 'hit_rate': 20}; operational observations {'BASKET_EVENT_OR_MISSING_OPEN': 20, 'INEFFECTIVE_NONPOSITIVE_STOP': 280}.
* D_M3_vol: financial failures {'positive_net_return': 20, 'beats_spy': 20, 'drawdown': 20}; operational observations {'INEFFECTIVE_NONPOSITIVE_STOP': 260}.

## Saved comparators — no repeated prior experiments

| Model | Net USD % | DD USD % | Sharpe | Fees USD |
|---|---:|---:|---:|---:|
| SPY same small account | 64.02 | -17.81 | 1.28 | 12.23 |
| Stocks10 A | 6.39 | -45.03 | 0.27 | 722.84 |
| Stocks10 B | 35.44 | -29.80 | 0.47 | 885.30 |
| v2 M1 | 43.59 | -36.41 | 0.52 | 841.08 |
| v2 M2 | 36.10 | -39.44 | 0.47 | 535.88 |
| v2 M3 | 19.83 | -52.65 | 0.36 | 416.37 |
| v2 Q10 | 34.08 | -29.83 | 0.48 | 435.63 |
| v2 QV | 18.14 | -52.20 | 0.35 | 419.46 |
| v2 C | 13.88 | -18.68 | 0.54 | 49.92 |
| H3 (100k USD, 15bp costs) | 77.13 | -16.08 | 1.31 | 3122.86 |
| Core (100k USD, 15bp costs) | 15.60 | -47.38 | 0.35 | 5701.84 |

H3/Core are saved large-account research controls with different capital/cost conditions. SPY is never a Momentum10 holding. Financial gates remain USD; SEK DD is shown separately and is not hidden.

## Drawdown, concentration, stops and independent checks

* R_M1_none: worst episode {'peak': '2024-12-26', 'trough': '2025-11-21', 'drawdown_pct': -56.63691889176115, 'recovered': None}; 0 stop fills, 0 below barrier. Max mean pair correlation at selection 0.3108349459653067; max biopharma-name hint slots 5 (unverified/incomplete).
* T_M1_none: worst episode {'peak': '2024-12-26', 'trough': '2025-11-21', 'drawdown_pct': -56.837572464109854, 'recovered': None}; 0 stop fills, 0 below barrier. Max mean pair correlation at selection 0.3108349459653067; max biopharma-name hint slots 5 (unverified/incomplete).
* D_M1_none: worst episode {'peak': '2024-12-26', 'trough': '2025-11-21', 'drawdown_pct': -56.837572464109854, 'recovered': None}; 0 stop fills, 0 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 5 (unverified/incomplete).
* D_M2_none: worst episode {'peak': '2024-11-29', 'trough': '2026-10-16', 'drawdown_pct': -69.83048144743269, 'recovered': None}; 0 stop fills, 0 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 4 (unverified/incomplete).
* D_M3_none: worst episode {'peak': '2024-11-11', 'trough': '2025-08-19', 'drawdown_pct': -55.52658264583804, 'recovered': None}; 0 stop fills, 0 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 3 (unverified/incomplete).
* D_M1_fixed10: worst episode {'peak': '2024-11-29', 'trough': '2025-11-21', 'drawdown_pct': -53.464109895413394, 'recovered': None}; 101 stop fills, 88 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 5 (unverified/incomplete).
* D_M2_fixed10: worst episode {'peak': '2025-01-06', 'trough': '2026-10-23', 'drawdown_pct': -48.14833031615865, 'recovered': None}; 80 stop fills, 70 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 5 (unverified/incomplete).
* D_M3_fixed10: worst episode {'peak': '2024-11-26', 'trough': '2025-08-07', 'drawdown_pct': -31.62539184074127, 'recovered': '2026-04-16'}; 69 stop fills, 61 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 3 (unverified/incomplete).
* D_M1_vol: worst episode {'peak': '2024-12-26', 'trough': '2025-11-21', 'drawdown_pct': -56.7603360513545, 'recovered': None}; 6 stop fills, 5 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 5 (unverified/incomplete).
* D_M2_vol: worst episode {'peak': '2024-11-29', 'trough': '2026-10-16', 'drawdown_pct': -65.85122021554473, 'recovered': None}; 12 stop fills, 11 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 4 (unverified/incomplete).
* D_M3_vol: worst episode {'peak': '2024-11-11', 'trough': '2025-08-19', 'drawdown_pct': -54.57405340712624, 'recovered': None}; 10 stop fills, 9 below barrier. Max mean pair correlation at selection 0.2693998936967242; max biopharma-name hint slots 3 (unverified/incomplete).

See the separately reconciled per-stock baseline drawdown attribution in `MOMENTUM10_V3_ATTRIBUTION_20261031.md` and its complete JSON. Monthly v2 AXTI contributed USD -513.59 (34.67% of its net drawdown-period loss); peak observed single-name weight reached 26.10%. Retained quantities permit weight drift.

All independent checks PASS. Largest daily accounting residual 9.09494701773e-13 USD. Full raw opening fills, fees, integer market quantities, native claims/FX, NAV, rankings, trend/cluster rules, retention, calendars, stop basis/blacklists and financial gates were checked. Same vendor is not independent market data.

Historical sector labels remain unavailable: no current SIC/GICS was injected into historical signals. Return clusters are observable risk groups, not industry classification. PIT-name hints are incomplete diagnostics only; they never affect decisions.

Paper candidate: None; financial candidate: None. No new paper account was started unless separately frozen for future-only observation; no broker orders/live approval.

All three preregistered selection mechanisms and the final finite 3×3 interval/stop matrix are preserved. If none qualifies, the supported register is exhausted: a more flattering historical combination is not a justified fourth hypothesis. Additional selection factors need new causal evidence and fresh preregistration, not reuse of these results as untouched validation.


## Verified interpretation

The new current-momentum score worsened monthly retention from saved v2 +43.59% to R -16.84%; the trend condition T returned -21.26%, and adding D clusters returned -19.63%. D reduced the maximum selection-time mean pair correlation from .3108 to .2694 while drawdown stayed -56.84%. Lower observed correlation alone did not control the damaging losses.
D monthly lost 45.85% in calendar 2025 versus SPY +16.70%. The predeclared quarterly fixed-stop contrast returned +11.21%, DD -31.63%, positive-month rate 48.48%, all below the applicable edge/risk/hit requirements. It is not promoted as a winning candidate. Its 69 stop fills included 61 below-barrier openings and a worst price-only entry loss of 47.89%, before fees.
RAPT cash completion is repaired in the v3-only event overlay. A new target basket committed before its 2026-03-03 merger could not be bought at that opening; the missing/untradeable RAPT slot was correctly blocked and fails operational admission. No substitute price, basket or historical paper fill was invented. Quarterly non-volatility cases avoid that operational block, but still fail financial GO.
Finite registered hypotheses R, T and D were each tested before proceeding; the final interval/stop matrix is complete. No evidence supports promotion, live trading or new automatic paper trading. Further selection-factor research requires a new causally supported registration and suitable dated inputs; these reviewed outcomes cannot be relabelled as independent future validation.
