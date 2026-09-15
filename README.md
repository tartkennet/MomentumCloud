# MomentumCloud Production v1

MomentumCloud är ett mobilanpassat beslutsstöd för en låst, lång amerikansk
portfölj med färskt 1–3-månadersmomentum. Systemet hämtar marknadsdata från Polygon, skapar tydliga
köp- och säljsignaler, uppdaterar Excel och publicerar samma verifierade
snapshot till dashboardens API.

## Produktionsregler

| Regel | Låst värde |
|---|---|
| Modell | `fresh-momentum-1-3m` |
| Portfölj | 15 aktier, lika vikt och minst 1 hel aktie per position |
| Omsättning | Månadsvis omallokering |
| Prisfilter | Minst 10 USD |
| Likviditet | ADV20 minst 5 000 000 USD |
| Instrument | Aktiva USA-noterade common stocks |
| Exkluderas | ETF, SPAC, ADR, preferensaktier |
| Marknadsregim | `SPY > SMA200` = RISK ON, annars 100 % kassa |
| Stop loss | 10 % |
| Ranking | 30 % 1 månad, 40 % 3 månader, 15 % 6 månader, 10 % låg volatilitet, 5 % låg SMA50-extension |
| Färskhetskrav | Positiv 1 och 3 månader, samt bättre än SPY under båda perioderna |
| Trendkrav | Kurs > SMA20 > SMA50 > SMA200; SMA50 och SMA200 ska stiga |
| Riskfilter | Högst 80 % annualiserad volatilitet och högst 20 % över SMA50 |

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

Systemet skickar inga order. Månadens kapitalanpassade `target_portfolio`
sparas oförändrad mellan de dagliga körningarna. `BuyNow` innehåller endast
köp som fortfarande är möjliga och inte finns i `Momentum_portfolio.csv`;
ett oexekverat månadsköp ligger därför kvar tills innehavet registreras.
Stoppade aktier blockeras från återköp till nästa månadsurval.

`Momentum_portfolio.csv` är den registrerade faktiska portföljen och
signalerna är beslutsunderlaget för nästa handelsöppning.

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
