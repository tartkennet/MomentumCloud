# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-24T06:26:29.010553+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-24 06:21:30,659 | INFO | Using cached security master with 5062 eligible securities
2026-09-24 06:21:30,741 | INFO | Grouped date 2026-09-24 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-24?apiKey=[REDACTED]&adjusted=true
2026-09-24 06:21:31,971 | WARNING | Polygon rate limit. Waiting 68.8s and retrying (1/6).
2026-09-24 06:22:41,134 | WARNING | Polygon rate limit. Waiting 74.9s and retrying (1/6).
2026-09-24 06:23:59,161 | INFO | Production output ready: 2026-09-23, 0 Buy Now, 50 candidates, RISK ON
2026-09-24 06:24:00,196 | INFO | Paper-close date 2026-09-24 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-09-24?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-09-24 06:24:00,618 | WARNING | Polygon rate limit. Waiting 68.0s and retrying (1/6).
2026-09-24 06:25:09,297 | WARNING | Polygon rate limit. Waiting 78.7s and retrying (1/6).
2026-09-24 06:26:28,128 | INFO | Paper portfolio refreshed: 2026-09-23, 10 positions, return=-5.3062%

```
