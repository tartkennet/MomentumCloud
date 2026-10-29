# MomentumCloud — verifiering 29 oktober 2026

PR #22 är färdig och sammanslagen. AEL, PLYA och RNA/RNAM har verifierade företagshändelser och full historisk bokföring. Den enda efterföljande rankingförbättringen är också färdigtestad. **Båda kandidaterna får NO_GO i samtliga 40 scenarier vardera.** GO-gränserna är oförändrade.

Gemensam period 2024-01-01–2026-10-28, USD efter kostnader, före skatt. Tabellen visar det fördefinierade fallet med 15 bp per sida, antagen betalning efter fem observerade sessioner och senaste observerade kurs under PLYA:s handelsstopp. Betaldatum är en känslighetsanalys, inte verifierade faktiska kontantbetalningar.

| Modell | Nettoavkastning | Maximal drawdown | Daglig Sharpe, RF=0 | Kostnader USD |
|---|---:|---:|---:|---:|
| Tidigare Core | +15.60 % | -47.38 % | 0.347 | 5701.84 |
| Normaliserad ranking, PR #22 | +62.48 % | -20.94 % | 0.843 | 6550.67 |
| Samma formationsperiod för avkastning och risk | +129.48 % | -36.26 % | 0.920 | 9014.98 |
| SPY | +68.08 % | -18.49 % | 1.293 | 149.60 |

Kod, alla scenarier, marknadsperioder och oberoende kontroller finns i [slutverifieringen](docs/CORE_FINAL_VALIDATION_20261029.md), [PR #22-resultaten](docs/CORE_NORMALIZED_REVIEW_20261029.md) och [uppföljningens resultat](docs/CORE_FORMATION_REVIEW_20261029.md). Alla 187 tester passerar. Grön CI betyder teknisk verifiering; den ändrar inte finansiellt NO_GO.

Underkända forskningsmodeller ligger separat från fryst Core, ursprunglig paper-identitet och Buy Now. Forskningsworkflowen är manuellt återkörbara från sparade data. Befintlig Core-paper fortsätter samla verkliga framtida sessioner; den utgör ingen validering av de ändrade forskningarnas regler. Redan granskad historik är utvecklingsdata och saknar ett orört out-of-sample-test. Verklig handel är inte godkänd.

Fryst Core använder 12–2-ranking, volatilitetsstyrd storlek och daglig SPY-riskkontroll. Reglerna finns i [Core-protokollet](docs/MOMENTUM_CORE_PROTOCOL.md).

```bash
python run_momentum_core.py --start 2024-01-01 --end 2026-09-01
python run_momentum_core.py --paper --start 2026-10-29 --output-dir core_paper_results
```

## Tidigare Production v1 / v4-balanced

MomentumCloud är ett mobilanpassat beslutsstöd för en låst, lång amerikansk
portfölj enligt v4-balanced med 12–2- och 6–2-månadersmomentum. Systemet hämtar marknadsdata från Polygon, skapar tydliga
köp- och säljsignaler, uppdaterar Excel och publicerar samma verifierade
snapshot till dashboardens API.

## Produktionsregler

| Regel | Låst värde |
|---|---|
| Modell | `v4-balanced` |
| Portfölj | 15 aktier, lika vikt och minst 1 hel aktie per position |
| Omsättning | Månadsvis omallokering |
| Prisfilter | Minst 10 USD |
| Likviditet | ADV20 minst 5 000 000 USD |
| Instrument | Aktiva USA-noterade common stocks |
| Exkluderas | ETF, SPAC, ADR, preferensaktier |
| Marknadsregim | `SPY > SMA200` = RISK ON, annars 100 % kassa |
| Stop loss | 10 % |
| Ranking | 55 % 12–2 momentum, 20 % 6–2 momentum, 15 % låg volatilitet, 10 % låg SMA50-extension |
| Momentumkrav | Positiv 12–2 och 6–2; den senaste månaden ingår inte i dessa signaler |
| Trendkrav | Kurs över både SMA50 och SMA200; SMA200 ska stiga |

Reglernas källa är `momentum_config.py` och `momentum_strategy.py`.

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

`validate_production_backtest.py` skriver `Momentum_validation_decision.json`.
Ett avbrott är `VALIDATION_ERROR`, inte ett numeriskt `NO-GO`. Olösta
positionsdata sammanställs i `Momentum_validation_data_errors.json`; inga
partiella prestationsmått får då användas för godkännande. Workflowet sparar
beslut och loggar även vid fel. Datacachen sparas separat för återanvändning.

Produktionen hämtar senaste avslutade main-valideringens artifact. Endast ett
GO med matchande källfingeravtryck och verifierade mått får godkännas av
`model_validation.py`; annars är Buy Now spärrat.

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
- `Production model validation`: manuellt samt vid relevanta kodändringar på
  main och PR från samma repo. Den använder samma v4-rankare som produktionen.

Återstående valideringsbegränsningar: det historiska backtestet och liveflödet
har ännu inte avstämts för malluniversum, dagliga regimbyten, tidpunkt för
månadsrotation och helaktieavrundning. Ett resultat för månadsbacktestet är
inte ensamt ett bevis för den exakta liveportföljens historik.

Full arkitektur, repo-audit och driftsinstruktioner finns i `docs/`.
