# MomentumCloud v3

A clean, production-ready momentum investing system built from scratch using Polygon as the only market data source.

## What it does

- Reads stock universe from `Momentum mall fil.xlsx` → `Universe` sheet (`Ticker` column).
- Pulls daily OHLCV data from Polygon.
- Applies quality filters:
  - Price >= 5 USD
  - Avg dollar volume (20d) >= 20,000,000 USD
  - Trend: Price > SMA50 > SMA200
  - Momentum: Ret3m > 0, Ret6m > 0, Ret12m > 0
- Scores stocks with weighted momentum + acceleration.
- Selects top 15, flags top 10 buy candidates.
- Reads portfolio value from `Parametrar!B1`.
- Calculates equal-weight qty for top 10 positions.
- Writes output to `Momentum.xlsx` / `BuyNow`.

## Required environment variable

- `POLYGON_API_KEY`: Polygon API key.

## Local run

```bash
pip install pandas numpy requests openpyxl
python momentum_master_v3.py
