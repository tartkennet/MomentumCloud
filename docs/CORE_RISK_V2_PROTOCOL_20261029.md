# Second fixed risk hypothesis and reserved extension — 29 October 2026

Study 1's entry-stop candidate was frozen at commit
93e06fd79610a1c08984b93d2bf387859dce8af6 before performance calculation.
Its development result improves returns and reduces drawdown, but does not
remove the 20% drawdown failure. Preserve that original attempt and source.

An entry-loss stop does not protect profits already accumulated above entry.
The earlier P&L attribution identifies a substantial peak-to-trough reversal.
Test ONE additional structural risk hypothesis: the same 10% threshold applied
to the highest completed close since entry. No threshold search, named-stock
exclusions, altered rank or weakened gate is permitted.

## Trailing variant fixed before inspecting extension performance

Track raw per-share high-water price. Initialize at the actual buy open and
update using each completed close. Additional buys cannot lower the reference;
a buy above the previous high raises it. Partial sales retain it. Verified
splits transform the reference per share. Verified stock exchanges transform
the reference by the same ratio; if an existing successor position is held,
combine the two references by resulting share count. This is a declared risk
transition, not a splice of two issuers' ranking histories.

On a completed close at/below 90% of that reference, sell tradable whole shares
at the next observed raw open, with the same costs and same-month cooldown as
the entry-stop candidate. No fill at a stop price, hindsight replacement or
forced sale of a fractional entitlement. This is price-based risk: dividends
remain separately accounted cash/receivables and can affect price triggers.
It does not guarantee a 10% trade loss or 20% portfolio drawdown limit.

## One complete comparison, no selective result

Keep the original baseline and entry-stop candidate. Run all THREE families
under all five original payment policies and both 15/30 bps costs: 30 historical
accounts. Every candidate and policy is then resumed into the same fixed
2026-09-02 through 2026-10-28 extension: 30 more accounts. No family/policy is
chosen before that extension. The second source/protocol must be committed
before inspecting any extension performance. Previously fetched market data
or current project snapshots do not make this a certified untouched holdout.

The initial Actions attempt detected a revised cached dividend vintage
(134624 events versus the original 134620) and correctly blocked baseline
reproduction before candidate evaluation. Use the exact original encrypted
cache key, not the latest mutable cache. Do not silently update the baseline.
Retain the failed run and compare input fingerprints explicitly.

All other details and economic gates remain as in the original study protocol.
Both hypotheses and every failure remain in the research register. All
historical passes are PAPER_ONLY. No real-money approval or order submission.
No further rule or threshold changes based on these extension outcomes.
