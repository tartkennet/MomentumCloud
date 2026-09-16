# MomentumCloud Production v1

Result: SUCCESS

Updated UTC: 2026-09-16T09:25:50.413942+00:00

Model: fresh-momentum-1-3m · positive 1m/3m and above SPY · 15 equal weights · monthly · ADV20 5M USD · stop 10% · SPY>SMA200

Current limitation: survivorship bias

## Log tail

```text
2026-09-16 08:18:23,252 | WARNING | Discarding unsafe security-master cache with only 2 securities
2026-09-16 08:18:23,599 | WARNING | Polygon rate limit. Waiting 75.3s and retrying (1/6).
2026-09-16 08:19:39,202 | WARNING | Polygon rate limit. Waiting 73.2s and retrying (1/6).
2026-09-16 08:20:52,621 | INFO | Grouped date 2026-09-16 unavailable: 403 Client Error: Forbidden for url: https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2026-09-16?apiKey=[REDACTED]&adjusted=true
2026-09-16 08:20:53,549 | WARNING | Polygon rate limit. Waiting 79.8s and retrying (1/6).
2026-09-16 08:22:14,425 | WARNING | Polygon rate limit. Waiting 71.1s and retrying (1/6).
2026-09-16 08:23:26,752 | WARNING | Polygon rate limit. Waiting 77.9s and retrying (1/6).
2026-09-16 08:24:45,947 | WARNING | Polygon rate limit. Waiting 79.9s and retrying (1/6).
2026-09-16 08:26:07,307 | WARNING | Polygon rate limit. Waiting 80.0s and retrying (1/6).
2026-09-16 08:27:28,608 | WARNING | Polygon rate limit. Waiting 65.9s and retrying (1/6).
2026-09-16 08:28:35,737 | WARNING | Polygon rate limit. Waiting 79.3s and retrying (1/6).
2026-09-16 08:29:56,240 | WARNING | Polygon rate limit. Waiting 76.7s and retrying (1/6).
2026-09-16 08:31:14,398 | WARNING | Polygon rate limit. Waiting 77.6s and retrying (1/6).
2026-09-16 08:32:33,321 | WARNING | Polygon rate limit. Waiting 79.7s and retrying (1/6).
2026-09-16 08:33:54,112 | WARNING | Polygon rate limit. Waiting 71.8s and retrying (1/6).
2026-09-16 08:35:07,210 | WARNING | Polygon rate limit. Waiting 73.4s and retrying (1/6).
2026-09-16 08:36:21,639 | WARNING | Polygon rate limit. Waiting 71.0s and retrying (1/6).
2026-09-16 08:37:33,867 | WARNING | Polygon rate limit. Waiting 69.0s and retrying (1/6).
2026-09-16 08:38:43,977 | WARNING | Polygon rate limit. Waiting 65.8s and retrying (1/6).
2026-09-16 08:39:51,105 | WARNING | Polygon rate limit. Waiting 77.1s and retrying (1/6).
2026-09-16 08:41:09,317 | WARNING | Polygon rate limit. Waiting 74.1s and retrying (1/6).
2026-09-16 08:42:24,656 | WARNING | Polygon rate limit. Waiting 75.9s and retrying (1/6).
2026-09-16 08:43:41,972 | WARNING | Polygon rate limit. Waiting 70.8s and retrying (1/6).
2026-09-16 08:44:53,984 | WARNING | Polygon rate limit. Waiting 72.7s and retrying (1/6).
2026-09-16 08:46:07,952 | WARNING | Polygon rate limit. Waiting 75.3s and retrying (1/6).
2026-09-16 08:47:24,446 | WARNING | Polygon rate limit. Waiting 68.1s and retrying (1/6).
2026-09-16 08:48:33,691 | WARNING | Polygon rate limit. Waiting 71.2s and retrying (1/6).
2026-09-16 08:49:45,786 | WARNING | Polygon rate limit. Waiting 66.9s and retrying (1/6).
2026-09-16 08:50:53,766 | WARNING | Polygon rate limit. Waiting 78.0s and retrying (1/6).
2026-09-16 08:52:12,960 | WARNING | Polygon rate limit. Waiting 76.1s and retrying (1/6).
2026-09-16 08:53:30,405 | WARNING | Polygon rate limit. Waiting 76.5s and retrying (1/6).
2026-09-16 08:54:48,187 | WARNING | Polygon rate limit. Waiting 78.9s and retrying (1/6).
2026-09-16 08:56:08,423 | WARNING | Polygon rate limit. Waiting 72.4s and retrying (1/6).
2026-09-16 08:57:22,004 | WARNING | Polygon rate limit. Waiting 69.2s and retrying (1/6).
2026-09-16 08:58:32,150 | WARNING | Polygon rate limit. Waiting 72.8s and retrying (1/6).
2026-09-16 08:59:46,231 | WARNING | Polygon rate limit. Waiting 76.2s and retrying (1/6).
2026-09-16 09:01:03,816 | WARNING | Polygon rate limit. Waiting 69.0s and retrying (1/6).
2026-09-16 09:02:13,973 | WARNING | Polygon rate limit. Waiting 75.6s and retrying (1/6).
2026-09-16 09:03:30,588 | WARNING | Polygon rate limit. Waiting 77.5s and retrying (1/6).
2026-09-16 09:04:49,300 | WARNING | Polygon rate limit. Waiting 70.6s and retrying (1/6).
2026-09-16 09:06:01,179 | WARNING | Polygon rate limit. Waiting 71.6s and retrying (1/6).
2026-09-16 09:07:13,753 | WARNING | Polygon rate limit. Waiting 78.3s and retrying (1/6).
2026-09-16 09:08:33,293 | WARNING | Polygon rate limit. Waiting 77.2s and retrying (1/6).
2026-09-16 09:09:51,749 | WARNING | Polygon rate limit. Waiting 68.6s and retrying (1/6).
2026-09-16 09:11:01,537 | WARNING | Polygon rate limit. Waiting 66.0s and retrying (1/6).
2026-09-16 09:12:08,431 | WARNING | Polygon rate limit. Waiting 78.8s and retrying (1/6).
2026-09-16 09:13:28,401 | WARNING | Polygon rate limit. Waiting 68.0s and retrying (1/6).
2026-09-16 09:14:37,462 | WARNING | Polygon rate limit. Waiting 66.0s and retrying (1/6).
2026-09-16 09:15:44,449 | WARNING | Polygon rate limit. Waiting 66.3s and retrying (1/6).
2026-09-16 09:16:51,923 | WARNING | Polygon rate limit. Waiting 77.2s and retrying (1/6).
2026-09-16 09:18:10,402 | WARNING | Polygon rate limit. Waiting 78.4s and retrying (1/6).
2026-09-16 09:19:29,923 | WARNING | Polygon rate limit. Waiting 72.4s and retrying (1/6).
2026-09-16 09:20:43,469 | WARNING | Polygon rate limit. Waiting 69.8s and retrying (1/6).
2026-09-16 09:21:54,248 | WARNING | Polygon rate limit. Waiting 72.3s and retrying (1/6).
2026-09-16 09:23:07,628 | WARNING | Polygon rate limit. Waiting 75.9s and retrying (1/6).
2026-09-16 09:24:25,030 | WARNING | Polygon rate limit. Waiting 79.8s and retrying (1/6).
2026-09-16 09:25:49,000 | INFO | Production output ready: 2026-09-15, 15 Buy Now, 50 candidates, RISK ON

```
