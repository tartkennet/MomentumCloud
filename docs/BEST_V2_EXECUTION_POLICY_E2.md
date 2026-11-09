# BEST v2 execution policy E2 — prospective registration 2026-11-09

No change to the momentum selector, model fingerprint, account cohort, initial
SEK25,000, economic NO_GO or legacy strategies. Effective no earlier than
2026-11-10T00:00:00Z and actual policy registration. No Monday fills.

Existing Massive/Polygon credential was observed 2026-11-09T20:54:26Z to return
HTTP200 / status DELAYED minute aggregates for all ten stocks and SPY. Latest
minute start 20:39Z, approximately fifteen-minute data delay. This does not
establish real-time trade or quote entitlement. Grouped Daily also returned200;
there is no evidence it was queried by the absent Monday in-window jobs.

Use unadjusted one-minute aggregates, newest completed bar only, no selection
of older/cheaper prices. Bar starts in 09:35..15:40 America/New_York, same actual
session date, positive volume, finite consistent OHLC, exact minute timestamp,
bar end <= actual observation, maximum age twenty minutes after bar end.
Observation/booking must be within 09:35..15:59 NY, weekdays and a provider-
observed session. Price is the actual completed minute CLOSE, not a daily open,
VWAP or alleged real-time executable quote. Book at observation time, retaining
price_as_of, raw minute, endpoint, provider status/delay and observation time.
Label DELAYED_MINUTE_PAPER_ASSUMPTION. No claim a real order could obtain it.

A decision and E2 registration must precede the minute's START. Never use a
Monday minute for Tuesday, pre/aftermarket, unfinished or excessively old bars.
Preserve original commitments; migration records the missed Monday and explicit
cancellation, then makes a new prospective commitment with SAME TEN ISSUERS.
Recompute whole quantities/2% limits from fresh verified completed closes, same
cash, costs and issuer/cluster caps. Never overwrite old decisions or capital.
If this cannot fund ten, trading is explicitly blocked, no cheap substitutes.

Initial formation is atomic: all ten prices, limits, cash and post-trade issuer/
cluster constraints must pass together. Otherwise no fills and every one of the
ten orders gets a specific reason (or ATOMIC_BASKET_BLOCKED). Partial holdings
are never represented as fully invested. Idempotency is commitment/day bound;
completed attempts are not replayed. Unsuccessful attempts may retry a NEWER
minute while the same future decision remains valid. Append receipts/outcomes,
never rewrite prior attempts. Benchmark is separately simulated at its own
verified SPY minute and is never a strategy holding.

After the window, record MISSED_OPEN_NO_BACKFILL once per session and ten
specific unfilled outcomes; leave a valid prospective intention for later days.
Provider authorization/empty/late/future/stale responses are distinct. Technical
readiness, configured scheduling and actual execution outcome are independent.
GitHub cron is best effort; active configuration is not a demonstrated on-time
run. Frequent staggered attempts span the whole E2 window; missed sessions must
fail the dedicated execution-outcome check AFTER durable publication.
