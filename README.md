# MomentumCloud · Momentum 10 BEST v2

Huvudappen har Översikt, Portfölj, Affärer, Statistik och Inställningar för ett
separat automatiserat **PAPER EXPERIMENT**. BEST v1, H3, Avanza 10 och Quality
finns i Inställningars arkiv med sina tidigare regler och journaler bevarade.

[Förregistrerat v2-protokoll](docs/MOMENTUM10_BEST_V2_PROTOCOL.md) ·
[Verifiering och faktisk datatäckning](docs/BEST_V2_STATUS.md) ·
[Originalkällor](docs/BEST_V2_SOURCE_MIRRORS.md) ·
[APP och separat tidig E1-komponent](docs/BEST_V2_APP_DIAGNOSTIC.md).

Alla tillgängliga daterade XNAS/XNYS/XASE-stamaktier inventeras, utan topp-100-
begränsning. Urval bygger på kursmomentum, relativ styrka, acceleration, volym,
riskjusterat momentum och trenduthållighet. Prisbindande uppköpsmönster, onormalt
låg volatilitet, misstänkta språng och översträckning filtreras generellt.
E1 är en separat bevakningslista; den handlar inte automatiskt och APP får inget
undantag. Saknade originalkällor stoppar urval, inte en genväg till svagare namn.

Tio individuella aktier väljs före kapital. Inga ETF:er eller SPY-innehav i
strategikontot. Cirka 25 000 SEK är ett mjukt mål; verkligt högre minimum gäller.
Minst en hel aktie per bolag reserveras först, sedan fördelas fler hela aktier
med courtage, valutaväxling, kursbuffert och exekveringsreserv. Ändrat kapital i
webbläsaren ändrar aldrig urvalet eller kontots redan bokförda startkapital.
Inga hårda sektorgränser eller krav på fem sektorer. Koncentration och gemensam
vårdexponering visas öppet; befintliga emittent- och korrelationsgränser gäller.

`/api/best-v2` läser den egna hashkedjade journalen på
`best-v2-observed-snapshots`. Daglig riskkontroll och månadsvis bibehållet urval
körs i aktiverad GitHub Actions med källbunden operationskontroll. Exakta antal
sparas före en framtida öppning; endast verkligt observerade positiva-volympriser
i 09.30–11.30 New York kan bokföra paperköp. Missade tillfällen efterregistreras
aldrig. Planerade köp är inga genomförda innehav. Historik och SPY-jämförelse
börjar först vid verkligt registrerad paperstart, med daterad FX och avstämning.

**Ekonomiskt NO_GO. Ingen riktig handel, mäklarkoppling eller ekonomisk GO.**
Teknisk aktivering kräver full inventering, tio verifierade stamaktier,
finansierade heltalsorder och oberoende signal-, kapital- och kontokontroller.
Produktionskontrollen läser åtta API:er och fem flikar vid 320/390/1440 px.
Äldre API:ers befintliga dataspärrar redovisas; de intygar inte v2:s funktion.

Tidigare huvudprodukt: [BEST v1-protokoll](docs/MOMENTUM10_BEST_PROTOCOL_V1.md),
[tidigare implementation](docs/BEST_IMPLEMENTATION_NOTES.md), `/best`, `/api/best`.

## Tidigare Avanza-huvudapp och bevarad dokumentation

# MomentumCloud · Momentum 10 för Avanza

Huvudappen på `/` har Översikt, Portfölj, Affärer, Statistik och Inställningar.
Avanza-urvalet från PR #40–41 är kapitaloberoende. Automatkontots nya startkapital beräknas efter urvalet (`AUTO_MINIMUM`) eller väljs uttryckligen; 20 000 SEK är varken krav eller tak. H3 och äldre forskning finns
under Inställningar → Forskningsarkiv; deras journaler och frysta regler bevaras.

`/api/avanza10` levererar endast det separata Avanza-kontot, med explicita
leverans-, automations- och finansieringsspärrar. Den vanliga portföljvyn blandar
aldrig in Quality-kontots affärer eller H3. `/api/quality` och äldre API:er finns kvar.

Se [Avanza paper-protokoll](docs/AVANZA10_APP_PROTOCOL.md) för körning, datakrav,
kostnader, beständig journal, revision och begränsningar. **PAPER ONLY**. Inget
livegodkännande, ingen broker-integration och inga riktiga order.

---

## Tidigare modeller och driftinformation

# MomentumCloud — historiskt verifierad kandidat, PAPER_ONLY

Forskningskandidaten **H3 klarar alla fem oförändrade finansiella GO-krav i samtliga 40 scenarier**, inklusive dubbla transaktionskostnader. Status är **PAPER_ONLY**: verklig out-of-sample-validering saknas och riktig handel är inte godkänd.

2024-01-01–2026-10-28, USD netto efter 15 bp per sida, fördefinierat femsessioners betalningsantagande:

| Modell | Netto | Max drawdown | Daglig Sharpe, RF=0 | Avgifter USD |
|---|---:|---:|---:|---:|
| Ursprunglig Core | +15,60 % | −47,38 % | 0,347 | 5701,84 |
| PR #23 | +129,48 % | −36,26 % | 0,920 | 9014,98 |
| **H3** | **+77,13 %** | **−16,08 %** | **1,307** | **3122,86** |
| SPY | +68,08 % | −18,49 % | 1,293 | 149,60 |

H3 behåller PR23:s momentumranking och fördelar risk mellan momentumaktierna och en bred SPY-kärna. Det befintliga marknadsbeslutet gäller hela portföljen: risk-off leder till försäljning vid nästa observerade öppning. Inga nya indikatorer, sökta gränsvärden eller sänkta GO-krav. Försöken med riskbudget/kassa och passiv kärna bevaras som NO_GO.

33 perioder och 66,67 % positiva perioder. Vid 30 bp per sida ger H3 +73,35 %, drawdown −16,48 % och fortsatt historiskt godkända krav. 212 tester och separata redovisnings-/allokeringskontroller passerar.

[Riskanalys, marknadsperioder och verifieringsbevis](docs/CORE_PORTFOLIO_RISK_REVIEW_20261029.md) · [Alla H3-scenarier](docs/CORE_PORTFOLIO_H3_REVIEW_20261029.md) · [Fryst framåtjournal](docs/CORE_PORTFOLIO_FORWARD_PROTOCOL_20261029.md) · [Tidigare PR22/23-verifiering](docs/CORE_FINAL_VALIDATION_20261029.md).

Forskningskandidaten och dess framåtjournal är separata från aktiv produktion, ursprunglig Core-paper och Buy Now. Framåtjournalen samlar faktiska framtida sessioner och spärrar retroaktiv rekonstruktion. Ingen framtida avkastning är ännu verifierad. Ursprunglig Core behåller sin frysta källidentitet och sitt [protokoll](docs/MOMENTUM_CORE_PROTOCOL.md). Avslutade historiska forskningsjobb är manuellt återkörbara från sparade data.

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
