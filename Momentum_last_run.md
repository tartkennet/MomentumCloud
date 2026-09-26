# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-26T00:04:33.973923+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-25 23:59:35,080 | INFO | Using cached security master with 5062 eligible securities
2026-09-25 23:59:35,316 | INFO | Grouped date 2026-09-25 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-25?apiKey=[REDACTED]&adjusted=true
2026-09-25 23:59:37,989 | WARNING | Polygon rate limit. Waiting 66.6s and retrying (1/6).
2026-09-26 00:00:45,040 | WARNING | Polygon rate limit. Waiting 79.1s and retrying (1/6).
2026-09-26 00:02:07,549 | INFO | Production output ready: 2026-09-24, 0 Buy Now, 50 candidates, RISK ON
2026-09-26 00:02:08,469 | INFO | Paper-close date 2026-09-26 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-26?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-26 00:02:08,542 | INFO | Paper-close date 2026-09-25 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-25?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-26 00:02:08,716 | WARNING | Polygon rate limit. Waiting 77.2s and retrying (1/6).
2026-09-26 00:03:26,620 | WARNING | Polygon rate limit. Waiting 65.9s and retrying (1/6).
2026-09-26 00:04:33,111 | INFO | Paper portfolio refreshed: 2026-09-24, 10 positions, return=-4.658%

```
