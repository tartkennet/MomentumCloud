# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-10-06T01:48:46.990015+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-10-06 01:48:40,267 | INFO | Using cached security master with 5062 eligible securities
2026-10-06 01:48:40,402 | INFO | Grouped date 2026-10-06 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-10-06?apiKey=[REDACTED]&adjusted=true
2026-10-06 01:48:41,400 | INFO | Adjusted 253 cached PSKY rows for split 1.0:2.0 on 2026-10-05
2026-10-06 01:48:41,401 | INFO | Adjusted 253 cached GPMT rows for split 10.0:1.0 on 2026-10-06
2026-10-06 01:48:44,800 | INFO | Production output ready: 2026-10-05, 0 Buy Now, 50 candidates, RISK ON
2026-10-06 01:48:45,621 | INFO | Paper-close date 2026-10-06 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-10-06?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-10-06 01:48:46,211 | INFO | Paper portfolio refreshed: 2026-10-05, 10 positions, return=1.7212%

```
