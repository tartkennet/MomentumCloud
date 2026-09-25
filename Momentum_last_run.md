# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-25T00:00:48.323319+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-24 23:55:37,687 | INFO | Using cached security master with 5062 eligible securities
2026-09-24 23:55:37,883 | INFO | Grouped date 2026-09-24 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-24?apiKey=[REDACTED]&adjusted=true
2026-09-24 23:55:39,128 | WARNING | Polygon rate limit. Waiting 76.8s and retrying (1/6).
2026-09-24 23:56:56,395 | WARNING | Polygon rate limit. Waiting 78.4s and retrying (1/6).
2026-09-24 23:58:17,654 | INFO | Production output ready: 2026-09-23, 0 Buy Now, 50 candidates, RISK ON
2026-09-24 23:58:18,328 | INFO | Paper-close date 2026-09-24 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-24?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-24 23:58:18,498 | WARNING | Polygon rate limit. Waiting 67.2s and retrying (1/6).
2026-09-24 23:59:26,039 | WARNING | Polygon rate limit. Waiting 81.1s and retrying (1/6).
2026-09-25 00:00:47,617 | INFO | Paper portfolio refreshed: 2026-09-23, 10 positions, return=-5.3062%

```
