# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-10-07T00:52:02.797223+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-10-07 00:51:55,835 | INFO | Using cached security master with 5062 eligible securities
2026-10-07 00:51:55,893 | INFO | Grouped date 2026-10-07 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-10-07?apiKey=[REDACTED]&adjusted=true
2026-10-07 00:52:00,260 | INFO | Production output ready: 2026-10-06, 0 Buy Now, 50 candidates, RISK ON
2026-10-07 00:52:01,009 | INFO | Paper-close date 2026-10-07 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-10-07?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-10-07 00:52:02,001 | INFO | Paper portfolio refreshed: 2026-10-06, 10 positions, return=0.645%

```
