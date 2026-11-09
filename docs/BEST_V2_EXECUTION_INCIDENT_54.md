# BEST v2 execution incident #54

2026-11-09 investigation. No Monday fills may be created. Existing account,
SEK25,000, ten quantities and every historical record must be retained.

GitHub's dated workflow-run API returned total_count=1 for BEST v2 on Nov9:
42678518390, created/started 18:56:14Z, successful. There are no run records at
14:32,14:52,15:32,15:52Z. Do not invent logs/empty provider responses for absent
runs. Actual collect ran 18:56:52..18:57:48Z (13:56..13:57 New York), outside
09:30..11:30. The reused observer never queried today's opening endpoint then.
Its completed daily sessions ended Friday Nov6, so process() also failed to
recognize Monday as a missed eligible session. This masked missing execution
behind technical PASS. Configured/active cron is not evidence it actually ran.

Read-only authenticated minute/snapshot/grouped capability probe is saved on
the repair branch and must run before choosing the new execution policy.

Authenticated probe 42699170183: minute endpoint HTTP200, status DELAYED,
response ticker matches all eleven requested symbols, adjusted=false, count3.
Snapshot HTTP200 but lastTrade absent; never rely on it as real-time execution.
Grouped Daily HTTP200/DELAYED, 11,961 records later that day. No evidence of a
403/404/empty opening response during absent jobs; scheduler omission is the
verified primary cause. Exact reason GitHub did not deliver earlier schedules
is not exposed by run metadata. Active config is only configuration proof.

E2 preregistered in 6c01e53 before any Nov10 data. Minute CLOSE paper pricing,
observed booking time, <=20-minute quote age, 09:35..15:40 NY price window,
09:51..15:59 NY observation attempts. Raw response captured immutably; no later
vendor revision can rewrite a booked paper price. Legacy observer is retained
for closes/events with pending removed, so the grouped-opening route is never
called for E2. Original missed commitment/capital and all historical arrays are
protected by append-only publisher checks. Recommit SAME TEN after newer
completed closes; no contemporaneous intraday price is used to fit a decision.

GitHub attempts now span minute12/32/52 during13..20UTC, plus existing daily
runs. No scheduling SLA is claimed. API detects absence of a current-session
execution receipt even if the configured workflow is active. Technical readiness,
filled count, every order reason and the missed-session diagnostic are separate.
Dedicated trading-outcome check runs after durable publication and fails on a
missed session or unavailable expected prices. No green technical stage implies
that the basket traded. Regular risk and monthly selection rules are unchanged.
