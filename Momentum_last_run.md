# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-10-03T00:34:55.072387+00:00

Model: v4-balanced · 55% 12–2 momentum · 20% 6–2 momentum · 15% low volatility · 10% low extension · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-10-03 00:34:47,267 | INFO | Using cached security master with 5062 eligible securities
2026-10-03 00:34:47,498 | INFO | Grouped date 2026-10-03 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-10-03?apiKey=[REDACTED]&adjusted=true
2026-10-03 00:34:52,514 | INFO | Production output ready: 2026-10-02, 0 Buy Now, 50 candidates, RISK ON
2026-10-03 00:34:53,397 | INFO | Paper-close date 2026-10-03 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v1/open-close/DINO/2026-10-03?apiKey=7MippgSypUSTpVph0oP5qFd_zYxzvV61&adjusted=true
2026-10-03 00:34:54,359 | INFO | Paper portfolio refreshed: 2026-10-02, 10 positions, return=-0.3674%

```
