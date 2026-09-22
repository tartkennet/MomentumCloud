# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-22T06:10:40.519777+00:00

Model: fresh-momentum-1-3m · positive 1m/3m and above SPY · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-22 06:05:45,101 | INFO | Using cached security master with 5066 eligible securities
2026-09-22 06:05:45,305 | INFO | Grouped date 2026-09-22 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-22?apiKey=[REDACTED]&adjusted=true
2026-09-22 06:05:46,491 | WARNING | Polygon rate limit. Waiting 71.5s and retrying (1/6).
2026-09-22 06:06:58,309 | WARNING | Polygon rate limit. Waiting 73.1s and retrying (1/6).
2026-09-22 06:08:14,187 | INFO | Production output ready: 2026-09-21, 15 Buy Now, 50 candidates, RISK ON
2026-09-22 06:08:15,005 | INFO | Paper-close date 2026-09-22 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-22?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-22 06:08:15,159 | WARNING | Polygon rate limit. Waiting 69.5s and retrying (1/6).
2026-09-22 06:09:25,301 | WARNING | Polygon rate limit. Waiting 74.2s and retrying (1/6).
2026-09-22 06:10:39,832 | INFO | Paper portfolio refreshed: 2026-09-21, 10 positions, return=-3.1338%

```
