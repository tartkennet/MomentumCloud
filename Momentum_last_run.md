# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-30T00:37:01.995405+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-30 00:36:54,157 | INFO | Using cached security master with 5062 eligible securities
2026-09-30 00:36:54,395 | INFO | Grouped date 2026-09-30 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-30?apiKey=[REDACTED]&adjusted=true
2026-09-30 00:36:59,204 | INFO | Production output ready: 2026-09-29, 0 Buy Now, 50 candidates, RISK ON
2026-09-30 00:37:00,061 | INFO | Paper-close date 2026-09-30 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-30?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-30 00:37:01,281 | INFO | Paper portfolio refreshed: 2026-09-29, 10 positions, return=-4.3138%

```
