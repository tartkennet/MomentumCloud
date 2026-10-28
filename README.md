# MomentumCloud — Core-kandidat och historisk v4

Senaste fullständiga Core-testet, 2024-01-01–2026-09-01: **NO_GO**.
Modellen gav **+44,305365 %**, SPY **+65,442500 %** och maximal daglig
nedgång var **−37,523834 %**. SPY- och drawdownkraven fallerar. De 129
funktionstesterna, offlineåterkörningen och den separata redovisningskontrollen
passerar i [den verifierade körningen](https://github.com/tartkennet/MomentumCloud/actions/runs/40772049150).
Paper-cohort v2 börjar först med signal 2026-10-29; den missade ursprungliga
starten bevaras som ett misslyckat försök. Verkliga köp är inte godkända.

Det aktiva omarbetningsarbetet är `momentum-core-v1`. Kandidaten ersätter
v4:s blandade ranking och individuella fasta stoppar med en enkel
12–2-ranking, volatilitetsstyrd storlek och daglig SPY-riskkontroll. Historik
och pappershandel använder samma handelsmotor, råpriser, utdelningar och
kostnad på faktiskt handlat belopp. Regler och begränsningar är frysta i
[`docs/MOMENTUM_CORE_PROTOCOL.md`](docs/MOMENTUM_CORE_PROTOCOL.md).

```bash
python run_momentum_core.py --start 2024-01-01 --end 2026-09-01
python run_momentum_core.py --paper --start 2026-10-29 --output-dir core_paper_results
```

Workflowet **Momentum Core candidate** kör tester, historisk replay och dubbel
handelskostnad på PR. Efter införande på main kör det framåtriktad
pappershandel på morgonen efter USA-sessionen. `Momentum_core_decision.json`
visar varje ekonomiskt krav och uppnått värde; samtliga affärer, dagligt NAV,
mål och källfingeravtryck sparas i workflowets artifact. `NO_GO` är ett giltigt
ekonomiskt testresultat; datafel ger `DATA_BLOCKED` och ett misslyckat jobb.
Grön CI betyder att beräkningen körde färdigt, inte att modellen fick GO.

Redan granskad historik är utvecklingsdata. Kandidaten har ingen automatisk
livebehörighet och dess pappersorder matas inte in i gamla Buy Now.
`v4-balanced` nedan bevaras som den tidigare implementationen och jämförelsen;
dess tidigare NO-GO får inte döpas om till ett Core-godkännande.
Efter införandet är de två gamla v4-workflowen manuella. De startar inte
längre dagliga snapshot- eller valideringsloopar. Den befintliga dashboarden
visar ett historiskt v4-snapshot tills en separat verifierad publicering finns.

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
