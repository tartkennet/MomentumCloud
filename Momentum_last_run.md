# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-23T05:57:29.357980+00:00

Model: fresh-momentum-1-3m · positive 1m/3m and above SPY · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-23 05:52:41,311 | INFO | Using cached security master with 5066 eligible securities
2026-09-23 05:52:41,624 | INFO | Grouped date 2026-09-23 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-23?apiKey=[REDACTED]&adjusted=true
2026-09-23 05:52:42,736 | WARNING | Polygon rate limit. Waiting 70.3s and retrying (1/6).
2026-09-23 05:53:53,193 | WARNING | Polygon rate limit. Waiting 74.5s and retrying (1/6).
2026-09-23 05:55:10,788 | INFO | Production output ready: 2026-09-22, 0 Buy Now, 50 candidates, RISK ON
2026-09-23 05:55:11,652 | INFO | Paper-close date 2026-09-23 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-23?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-23 05:55:11,802 | WARNING | Polygon rate limit. Waiting 66.3s and retrying (1/6).
2026-09-23 05:56:18,467 | WARNING | Polygon rate limit. Waiting 69.8s and retrying (1/6).
2026-09-23 05:57:28,537 | INFO | Paper portfolio refreshed: 2026-09-22, 10 positions, return=-5.3408%

```
