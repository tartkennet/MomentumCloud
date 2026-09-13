# MomentumCloud Production v1

MomentumCloud är ett mobilanpassat beslutsstöd för en låst, lång amerikansk
momentumportfölj. Systemet hämtar marknadsdata från Polygon, skapar tydliga
köp- och säljsignaler, uppdaterar Excel och publicerar samma verifierade
snapshot till dashboardens API.

## Produktionsregler

| Regel | Låst värde |
|---|---|
| Modell | `v4-balanced` |
| Portfölj | 15 aktier, lika vikt |
| Omsättning | Månadsvis omallokering |
| Prisfilter | Minst 10 USD |
| Likviditet | ADV20 minst 5 000 000 USD |
| Instrument | Aktiva USA-noterade common stocks |
| Exkluderas | ETF, SPAC, ADR, preferensaktier |
| Marknadsregim | `SPY > SMA200` = RISK ON, annars 100 % kassa |
| Stop loss | 10 % |
| Ranking | 55 % 12–2, 20 % 6–2, 15 % låg volatilitet, 10 % låg SMA50-extension |

`Current limitation: survivorship bias`

Det befintliga universumet i arbetsboken används som startmängd och korsas
med Polygons aktuella instrumentregister. Begränsningen visas i dashboard,
Excel och valideringsresultat.

## Körning

```bash
python -m pip install -r requirements.txt
export POLYGON_API_KEY="..."
python momentum_production.py
```

Körningen skapar `Momentum.xlsx`, `Momentum_signals.csv`,
`Momentum_buy_history.csv`, `public/data/dashboard.json` och
`public/data/buynow.json`.

Systemet skickar inga order. `Momentum_portfolio.csv` är den registrerade
portföljen och signalerna är beslutsunderlaget för nästa handelsöppning.

## App och API

- Dashboard: `public/index.html`
- Senaste snapshot: `GET /api/dashboard`
- Hälsokontroll: `GET /api/health`
- Hosting: Vercel via `vercel.json`

## Automation

- `Production CI`: syntax, unit-tester och konfigurationslås.
- `MomentumCloud Production v1`: vardagskvällar efter USA-stängning. Modellen
  roterar endast månadsvis men uppdaterar priser, riskregim och stoppsignaler
  varje handelsdag.
- `Production model validation`: manuell backtest av exakt samma v4-modell.

Full arkitektur, repo-audit och driftsinstruktioner finns i `docs/`.

