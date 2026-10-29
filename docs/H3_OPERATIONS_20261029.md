# Frozen H3 paper operations

## Verified installation before the first market observation

The frozen source remains commit `80489e3d7fa95842737981d44525598d54212bbb`. The main supervisor restores that source from the existing draft release and verifies every archived file against its committed Git blob. It runs the original 212 frozen tests. The separate observer never imports the strategy, ledger or metric implementation.

PR25 stage-one paper run [40874807620](https://github.com/tartkennet/MomentumCloud/actions/runs/40874807620) completed successfully. It restored the frozen archive, restored and authenticated/decrypted the existing saved inputs using the configured key, ran the frozen tests, made bounded read-only data probes, ran the unchanged waiting engine, re-encrypted the cache, uploaded immutable run/attempt evidence and advanced the durable release pointer last. The Actions API reported workflow state `active`. Required SPY raw daily bars, dated common-stock reference data, splits and dividends each returned HTTP 200. The latest available SPY session in that probe was 2026-10-28. Historical quotes returned HTTP 403; this is an explicit execution-evidence limitation, not a reason to invent a spread or buy another subscription.

No paper trading session or simulated fill existed at that time. Status was `PAPER_WAITING_FOR_SESSIONS`, with null actual performance and no holdings or forward curve. The first-stage artifact was ID `12897432932`, SHA-256 `00311370d9547e4648ddf19ad0335e94d88c61fc237efad1c4a0c6874ff05a47`.

## Schedule and restart behavior

`.github/workflows/core_portfolio_forward.yml` is registered on main with UTC cron `35 0,3,6,9 * * 2-6`, a fixed concurrency group and no overlapping/cancelled paper runs. This is Tuesday–Saturday morning collection following US sessions. GitHub schedule starts can be delayed.

For the completed US session 2026-10-29, the first scheduled attempt is **2026-10-30 00:35 UTC / 01:35 Europe/Stockholm**. Retry slots are 03:35, 06:35 and 09:35 UTC. The original intention deadline is 12:00 UTC / 13:00 Stockholm, ahead of the next US open. The first observation requires real final daily inputs; it is not manufactured during installation. A first recorded signal can only fill at the next observed session's raw open, and that simulated fill is only reported once that real session's data have been collected.

The unchanged engine processes at most one previously unrecorded market session. Weekends and holidays add no fake sessions. Rerunning an accepted date must retain the entire account state. A genuine gap of multiple missed sessions blocks retrospective intermediate decisions. Independent rejection quarantines the new attempt; accepted history is restored, intentions are cleared in the current error report, and failures remain visible. Existing archive names are never overwritten. The latest pointer advances after its immutable archive and inactive encrypted cache slot; a failed encryption cannot replace the last authenticated input pointer.

## Dashboard and acceptance

The existing dashboard gains `#h3-paper` and `/api/h3`. The server reads the separately published observation branch without exposing a market-data key. The browser shows only accepted forward NAV, SPY, holdings, decisions, simulated trades, daily drawdown, descriptive Sharpe, costs, daily session count, complete monthly periods, errors and next expected attempt. Historical results are labelled separately. A missing remote export returns HTTP 503 and an unverified older fallback; a missed publication beyond the declared 90-minute monitoring grace clears displayed intentions and reports delay. This grace does not relax the engine's prospective deadline.

The observer reconstructs new cash, holdings, receivables, corporate events, raw-open prices, whole-share target sizing, cash scaling, fees and closing NAV independently in all four accounts. It checks the new raw/event/calendar vintage digests and all previously accepted equity, trade and target rows. It computes metrics independently and retains the first complete 30-period verdict. The frozen five gates, 15/30bp stress requirement and execution limitations are set out in [the acceptance protocol](H3_FORWARD_ACCEPTANCE_PROTOCOL_20261029.md) and `h3_forward_policy.json`.

The opening partial month does not count. Full financial assessment is possible after the first observed May 2029 close at the earliest, with 30 full observed monthly intervals; daily session count is reported independently. Financial success is `FORWARD_PASS_REVIEW_REQUIRED`, never automatic live approval. Spread, opening depth and actual brokerage fees currently remain unverified. No broker integration, real orders, active Core model, prior results or Buy Now logic is changed.
