# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-23T23:56:37.179757+00:00

Model: quality-momentum-v2 · positive 1m/3m and above SPY · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-23 23:49:03,024 | WARNING | Polygon rate limit. Waiting 75.5s and retrying (1/6).
2026-09-23 23:50:19,354 | WARNING | Polygon rate limit. Waiting 72.9s and retrying (1/6).
2026-09-23 23:51:32,665 | INFO | Grouped date 2026-09-23 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-23?apiKey=[REDACTED]&adjusted=true
2026-09-23 23:51:33,895 | WARNING | Polygon rate limit. Waiting 79.9s and retrying (1/6).
2026-09-23 23:52:54,192 | WARNING | Polygon rate limit. Waiting 70.7s and retrying (1/6).
2026-09-23 23:54:08,019 | INFO | Production output ready: 2026-09-22, 0 Buy Now, 49 candidates, RISK ON
2026-09-23 23:54:08,857 | INFO | Paper-close date 2026-09-23 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-23?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-23 23:54:08,997 | WARNING | Polygon rate limit. Waiting 66.1s and retrying (1/6).
2026-09-23 23:55:15,511 | WARNING | Polygon rate limit. Waiting 80.4s and retrying (1/6).
2026-09-23 23:56:36,351 | INFO | Paper portfolio refreshed: 2026-09-22, 10 positions, return=-5.3408%

```
