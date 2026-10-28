# Cash timing diagnostic — fixed before running results

This experiment diagnoses one known accounting limitation of frozen Core v1.
It does not change selection, ranking, weights, market regime, costs, performance
thresholds or the production decision. No scenario authorizes live orders.

Use the complete saved 2024-01-01 through 2026-09-01 input snapshot. First
reproduce the original baseline metrics and ledger exactly. Then run every
predefined hypothetical payment delay: 0, 1, 5 and 20 observed trading sessions
after the cash merger's effective date. Run each at 15 and 30 bps per side.
Apply each delay to ALL verified cash mergers lacking a payment date, not just
profitable names or positions held in the baseline. Preserve verified payment
dates. Keep contingent rights unpriced and nonspendable.

These dates are ASSUMPTIONS, not historical payment facts. Neither the immediate
case nor a delayed case is a mathematical upper/lower performance bound. Report
all scenarios and any data failure; do not choose the winning assumption. Missing
new inputs/events block a scenario. No network access and no replacement data.

Cache only pure date-based signals within this one experiment. Prove that the
unmodified baseline reproduces the previously exported daily ledger, trades,
periods, targets, final state, source fingerprint and used-input fingerprint.
Independently reconcile each completed base-cost scenario against raw data using
the existing accounting auditor with the same explicitly assumed payment facts.
This checks arithmetic, not actual historical settlement.

Record the protocol hash before execution, then source/input/assumption hashes,
all outputs and the full attempt register. The inspected period is DEVELOPMENT;
even all economic PASS means only a hypothetical historical pass, never GO.

Stop after the fixed batch. Do not iterate rules/thresholds to force acceptance.
