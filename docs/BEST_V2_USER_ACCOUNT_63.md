# Explicit user simulation start (#63)

Account `best-v2-user-simulation-2026-11-09` is the ONE followed paper account.
The user explicitly selected the saved counterfactual Nov9 opening portfolio,
including FIGS despite its breached former limit. Its ten initialization entries
are **SIMULATED_HISTORICAL_INITIALIZATION**, never actual prospective executions.
`execution_at=null`, `actual_execution=false`, historical effective date Nov9,
real `recorded_at`/`registered_at`, immutable source snapshot and content hash.

`data/best-v2-user-start.json` is an exact saved copy of the existing
`public/data/best-v2-paper-start.json`. Original source remains intact. New
initialization independently checks all ten recorded opens AND closes against
actual unadjusted dated provider bars. Cash starts at SEK25,000 / saved ECB FX;
each buy charges max(USD1, 0.25% notional) +0.25% FX +0.15% execution reserve.
Initial cash SEK350.946921809; saved Nov9 NAV SEK25,337.650388, +SEK337.650388
(+1.350601552%). No hypothetical SPY start or guaranteed real fill is invented.

The original machine experiment state, journal and snapshots stay unchanged in
`best-v2-observed-snapshots`. Its scheduled publication/execution is frozen;
PR-only research tests remain. The new account writes only
`best-v2-user-snapshots`, with immutable per-run observations, an append-only
trade/valuation/event/decision audit, state-hash chain and no Vercel deployments
from the data branch. Idempotent restoration makes a second initial purchase
impossible. A different initialization source/account is rejected.

Reuse frozen BEST selector, same E2 observed-minute engine, same costs/risk
controls. All TEN current issuers still need current source checks. November
membership is already established. No new initial order. December full-universe
selection keeps qualifying whole-share holdings, sells others and prospectively
plans new members; capital does not change ranking. Daily SPY risk-off can
prospectively sell holdings before December. Original initialization cannot be
made to pass the former prospective order constraints retroactively.

A separate independent seeded-ledger replay checks initialization using Decimal
formulas, then all future corporate events, cash, fees, trades, holdings and NAV.
Prospective trades additionally pass the existing raw-minute execution audit.
Unfilled orders, source errors and missed sessions stay visible. Failed refreshes
preserve last accepted holdings/values and publish BLOCKED, never zero them.

Workflow `best_v2_user.yml` validates actual main workflow activation and updates
on staggered :12/:32/:52 UTC hours13–20, morning08:22 and20:20/21:20UTC closes.
Winter21:20UTC equals22:20 Stockholm; the earlier close slot cannot use an
unfinished daily bar. GitHub scheduling has no SLA. Encrypted incremental input
cache uses existing provider secret; no keys in public reports or source.

All five tabs consume the SAME account API. Remove the read-only reconstruction
overlay so it cannot override future sales/returns or create duplicate tables.
Preserve dark theme/mobile holding cards, names/quantities/current values.
Original reconstruction documents and script remain archived. Future returns
include this historical simulation start, explicitly labeled; no economic GO,
real funds, broker integration, or original-machine execution claim.
