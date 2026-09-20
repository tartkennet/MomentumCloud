# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-20T07:45:43.916147+00:00

Model: fresh-momentum-1-3m · positive 1m/3m and above SPY · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-20 07:43:01,153 | INFO | Using cached security master with 5066 eligible securities
2026-09-20 07:43:01,571 | INFO | Grouped date 2026-09-20 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-20?apiKey=[REDACTED]&adjusted=true
2026-09-20 07:43:01,697 | INFO | Grouped date 2026-09-19 unavailable: No USDSEK result for 2026-09-19
2026-09-20 07:43:03,862 | WARNING | Polygon rate limit. Waiting 80.4s and retrying (1/6).
2026-09-20 07:44:24,894 | WARNING | Polygon rate limit. Waiting 74.8s and retrying (1/6).
2026-09-20 07:45:43,031 | INFO | Production output ready: 2026-09-18, 15 Buy Now, 50 candidates, RISK ON

```
