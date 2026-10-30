# H3 collection monitor, 30 October 2026

## Verified incident

The production portfolio API at 08:49 UTC served one accepted session (29 October),
RISK ON, USD 100,000 cash and no fills. Both the paper run 41013485761 attempt 1
and its automatic SEK valuation 41013599161 succeeded. Independent source,
prefix and four-account reconciliation passed; durable preservation and publication
also succeeded. The journal retained 16 pending targets: 15 momentum stocks and SPY.
SPY target weight was 78.0442800778%; the momentum sleeve was 21.9557199222%.

The published monitor expected the next cron slot at 06:35 UTC. No newer H3
publication arrived by 08:05 UTC (06:35 plus the unchanged 90-minute grace).
Consequently `/api/portfolio` added the delay error, suppressed current intentions,
and the UI displayed “Kontroll behövs”. This was a missing scheduled follow-up,
not a failed valuation, missing first session, lost holdings or Vercel build error.
GitHub's run list showed no run created for the missed follow-up. The provider's
internal reason for not delivering that trigger is not exposed by the run API.
GitHub documents that scheduled events may be delayed or dropped under load:
https://docs.github.com/en/actions/how-tos/troubleshoot-workflows

## Recovery and corrections

Run 41013485761 attempt 2 was explicitly retried. It succeeded at 08:52 UTC and
published a no-op acceptance with the original single session and no new fills.
Its automatic downstream SEK valuation 41029359965 also succeeded. No missed
session, signal or historical fill was reconstructed.

The original four-slot cron and frozen source remain unchanged. A second event
path now invokes the same serialized H3 workflow after a successful existing
`Momentum Core candidate` main-branch workflow. This is an independent recovery
trigger, not a dependency on Core signals or parameters. It uses existing access,
retains all frozen deadlines, and cannot guarantee GitHub platform availability.
The workflow-run event accepts only this repository's successful main runs.

The UI now distinguishes the next future planned cron slot from the missed
publication deadline; advancing the displayed clock never clears the 90-minute
alarm. Registered pending intentions are shown separately from fills, only when
publication and valuation are verified. Missing/stale publication still suppresses
current intentions. No opening prices, quantities or completed trades are guessed.

## Expected first fills

The 29 October intentions were recorded before the original prospective deadline.
They target the next observed session's actual opening prices, expected on Friday
30 October at 09:30 New York / 14:30 Stockholm. The frozen engine books these only
once that completed session's real daily inputs are available and independently
accepted, normally in Saturday 31 October's morning collection (first configured
slot 00:35 UTC / 01:35 Stockholm). The opening time is a simulation assumption,
not a broker fill. Missing opens or events can alter/cancel simulated fills under
the existing rules. Nothing is inserted into the journal before observation.

## Verification

Targeted delivery regression tests cover overdue clocks, unchanged alarm grace,
weekend/DST slots, recovery, intention suppression, and no fabricated holdings or
fills. GitHub CI and deployed browser/API checks are recorded in the PR.
H3 strategy, original identity, validation thresholds, live flags, API subscription,
and Buy Now are unchanged. Status remains PAPER_ONLY.
