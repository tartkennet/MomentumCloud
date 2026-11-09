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
