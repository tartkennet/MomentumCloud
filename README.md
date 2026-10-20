# MomentumCloud Production v1

MomentumCloud är ett mobilanpassat beslutsstöd för en låst, lång amerikansk
portfölj med datumkorrekt 12–2-, 6–2- och 3-månadersmomentum. Systemet hämtar marknadsdata från Massive, skapar tydliga
köp- och säljsignaler, uppdaterar Excel och publicerar samma verifierade
snapshot till dashboardens API.

## Produktionsregler

| Regel | Låst värde |
|---|---|
| Modell | `core-momentum-v1` |
| Portfölj | 12 aktier, lika vikt och minst 1 hel aktie per position |
| Omsättning | Månadsvis omallokering |
| Prisfilter | Minst 5 USD |
| Likviditet | ADV20 minst 5 000 000 USD |
| Instrument | Aktiva USA-noterade common stocks |
| Exkluderas | ETF, SPAC, ADR, preferensaktier |
| Marknadsregim | `SPY > SMA200` = RISK ON, annars 100 % kassa |
| Stop loss | 10 % |
| Ranking | 50 % 12–2-momentum, 30 % 6–2-momentum, 20 % 3-månadersmomentum |
| Trendkrav | Kurs över en stigande SMA200 |
| Daglig exit | 10 % stop-loss eller kurs under SMA200 |
| Månadsvis omallokering | Ny topp-12-portfölj vid månadsskifte |

`Current limitation: survivorship bias`

Live-urvalet använder hela det aktuella amerikanska common-stock-registret.
Backtestet använder en separat point-in-time-snapshot per signalmånad och
sparar det dataarkiv som krävs för reproducering.

Den första valideringen på Stocks Starter använder formningsdata från hösten
2021 och testperiod från 1 februari 2023. Det ger över 30 kompletta
månadsperioder utan att begära data utanför femårsplanens gräns.

## Körning

```bash
python -m pip install -r requirements.txt
export POLYGON_API_KEY="..."
python momentum_production.py
```

Körningen skapar `Momentum.xlsx`, `Momentum_signals.csv`,
`Momentum_buy_history.csv`, `public/data/dashboard.json` och
`public/data/buynow.json`.

Systemet skickar inga order. Månadens kapitalanpassade `target_portfolio`
sparas oförändrad mellan de dagliga körningarna. `BuyNow` innehåller endast
köp som fortfarande är möjliga och inte finns i `Momentum_portfolio.csv`;
ett oexekverat månadsköp ligger därför kvar tills innehavet registreras.
Stoppade aktier blockeras från återköp till nästa månadsurval.

`Momentum_portfolio.csv` är den registrerade manuella portföljen och
signalerna är beslutsunderlag. Systemet skickar aldrig order.

Den separata modellvalideringen använder point-in-time-universum och ger
`GO` endast vid minst 30 perioder, positiv nettoavkastning, bättre resultat
än SPY, daglig maximal nedgång högst 20 procent och minst 50 procents
träffsäkerhet. Ett misslyckat krav ger `NO-GO`; resultatet optimeras inte om
i efterhand.

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
