# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-10-16T23:44:09.009587+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-10-16 23:44:01,286 | INFO | Grouped date 2026-10-16 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/ticker/C:USDSEK/range/1/day/2026-10-16/2026-10-16?apiKey=[REDACTED]&adjusted=true&limit=10
2026-10-16 23:44:06,324 | INFO | Production output ready: 2026-10-15, 0 Buy Now, 50 candidates, RISK ON
2026-10-16 23:44:08,238 | INFO | Paper portfolio refreshed: 2026-10-16, 10 positions, return=5.686%

```
