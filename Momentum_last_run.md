# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-10-09T01:18:15.270179+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-10-09 01:18:08,214 | INFO | Grouped date 2026-10-09 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-10-09?apiKey=[REDACTED]&adjusted=true
2026-10-09 01:18:12,919 | INFO | Production output ready: 2026-10-08, 0 Buy Now, 50 candidates, RISK ON
2026-10-09 01:18:13,679 | INFO | Paper-close date 2026-10-09 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-10-09?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-10-09 01:18:14,642 | INFO | Paper portfolio refreshed: 2026-10-08, 10 positions, return=4.8807%

```
