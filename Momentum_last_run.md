# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-10-23T23:53:44.206972+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-10-23 23:53:38,965 | INFO | Grouped date 2026-10-23 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/ticker/C:USDSEK/range/1/day/2026-10-23/2026-10-23?apiKey=[REDACTED]&adjusted=true&limit=10
2026-10-23 23:53:42,282 | INFO | Production output ready: 2026-10-22, 0 Buy Now, 50 candidates, RISK ON
2026-10-23 23:53:43,504 | INFO | Paper portfolio refreshed: 2026-10-23, 10 positions, return=4.4298%

```
