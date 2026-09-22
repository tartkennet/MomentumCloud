# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-22T00:14:30.197053+00:00

Model: fresh-momentum-1-3m · positive 1m/3m and above SPY · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-22 00:12:06,313 | INFO | Using cached security master with 5066 eligible securities
2026-09-22 00:12:06,512 | INFO | Grouped date 2026-09-22 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-22?apiKey=[REDACTED]&adjusted=true
2026-09-22 00:12:06,561 | INFO | Grouped date 2026-09-21 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-21?apiKey=[REDACTED]&adjusted=true
2026-09-22 00:12:06,765 | INFO | Grouped date 2026-09-19 unavailable: No USDSEK result for 2026-09-19
2026-09-22 00:12:07,854 | WARNING | Polygon rate limit. Waiting 71.0s and retrying (1/6).
2026-09-22 00:13:19,050 | WARNING | Polygon rate limit. Waiting 67.5s and retrying (1/6).
2026-09-22 00:14:29,463 | INFO | Production output ready: 2026-09-18, 15 Buy Now, 50 candidates, RISK ON

```
