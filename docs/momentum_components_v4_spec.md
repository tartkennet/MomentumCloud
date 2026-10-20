# Momentum components v4: fixed experiment, 20 October 2026

Authorized task: separate stock ranking, sizing, stops, market rules and costs. This specification is fixed before computing any new component aggregate returns. No parameter grid or threshold tuning follows the results.

## Frozen choices and factors

Use the existing v3 broad eligible universe, 25 slots and both already declared ordinary/risk-adjusted 50/30/20 momentum ranks. Recompute the same 43 signal rankings on the frozen October 6 basis, including the four previously cash signals so an unconditional reference is possible. Existing 39 risk-on choices and full-model gross results must match v3. Do not replace an unavailable trade or redistribute its weight.

Run the full 2x2x2 factorial for three Boolean risk components for each ranking (16 predeclared cases total):

* W: capped inverse-volatility weights and unlevered 15% covariance risk target. Without W, each selected slot has weight 1/25, including missing/canceled slots as cash.
* S: existing 10% close-detected stop, executed at the next actual open. Without S hold to rebalance, market exit or documented cash settlement.
* M: the existing monthly SPY/SMA200 entry gate AND daily SPY/SMA200 exit, no intramonth reentry. Without M, buy all 43 monthly signals and disable market exits. This experiment evaluates that combined market policy, not its two pieces separately.

The zero-factor reference has equal weights, no stock stop and no market gate. Show each factor alone, cumulative paths and the all-factor case. Explain interactions rather than choosing a best row after inspection. Preserve all eight cases for both rankings, including negative/blocked outcomes.

## Execution and evidence

Observed next-open executions and existing documented corporate-action unit converters remain mandatory. Retain v3's documented canceled-entry orders and paired-source-confirmed stale-close convention, labeling every affected variant provisional. A missing unknown observation blocks that case; it is never a silent exclusion. Preserve missing evidence in outputs. No live trading or model activation.

## Costs and self-financing ledger

The previous fixed 0.30% of total capital per invested month remains a separately labeled bridge/stress row. Also show gross diagnostics.

New order-level cost is max(proportional commission * market notional, minimum USD commission) + FX rate * notional + assumed half-spread * notional + assumed slippage * notional. Charge both buys and sells. Zero fills have no cost. Cash mergers have an FX-only conversion charge in automatic-conversion scenarios, with no fictional market order or commission. Other successor-market sales use the existing converted consideration, a disclosed approximation for mixed consideration.

Declared illustrative account sizes: USD 10,000 (primary), USD 100,000 (minimum-fee sensitivity), not the user's actual account value. Price returns remain USD; this does not include the market return of USD/SEK. Fractional holdings remain a research approximation. Unknown broker class, current US minimum fee and actual spreads/fills are not asserted as known.

Three scenarios, applied to all cases without selecting favorable ones:

| Scenario | Commission | Minimum | Automatic FX each buy/sell | Half-spread | Slippage |
|---|---:|---:|---:|---:|---:|
| fee_only_lower_bound | 0.25% | USD 1 | 0.25% | 0 | 0 |
| central_assumption | 0.25% | USD 1 | 0.25% | 0.05% | 0.05% |
| execution_stress | 0.25% | USD 1 | 0.25% | 0.25% | 0.25% |

FX 0.25% is supported by Avanza's currently retrieved explanation. Commission/minimum is a declared Mini-style scenario supported by an older official announcement, not confirmation of the user's current tariff. Spread/slippage are sensitivity assumptions, not observed quotes. These scenarios can be more costly than the old fixed deduction; do not lower assumptions to improve performance. No taxes, dividends, cash interest or unmodeled special regulatory fees are included.

At each monthly open, net continuing same-ticker shares against the new target so only quantity changes incur order costs. Carry is allowed only for a normal rebalance with no corporate-action unit change and matching observed old-exit/new-entry prices. All earlier stops/market exits are real sales. Stop reference resets at each signal's new monthly opening reference even for retained shares, matching the old monthly-lot policy.

Reserve entry/rebalance fees from available equity: solve a common post-fee allocation budget, keep any rounding residual as cash, then execute net orders. Do not borrow or charge costs on a nonexistent sell/rebuy. Intramonth sale fees reduce cash at their execution dates; final liquidation fees are charged once. Maintain self-financing cash/holdings and timestamped orders, not just a final-return haircut. Gross paths, fixed-cost bridge paths and order-cost paths remain distinct accounting conventions.

SPY price buy-and-hold is an order-cost benchmark with one initial buy and one final sell, no fictional monthly round trips. Matched-initial-exposure SPY controls use each model's monthly exposure and market policy; they do not reproduce individual stock stops and are not pure alpha attribution.

## Validation and decision

Test no-cost parity, netting, both-sided/minimum costs, funding, dated fee deductions, cash mergers and cancellations. Independently reconstruct cash/equity/cost totals and 43 monthly endpoints from retained orders, quantities and unit marks. Reproduce all-factor v3 gross/monthly returns before accepting comparisons. Freeze source/input hashes. Do not describe existing history as untouched holdout: all 43 periods were previously inspected. An unseen forward test can be specified but cannot be completed with future observations. Report which effects are consistent, which depend on interactions and what remains unverified. A historical winning row is not automatically approved for investment.
