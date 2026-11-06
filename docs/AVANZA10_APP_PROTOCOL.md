# Momentum 10 Avanza · huvudapp och separat observerat paperkonto

Modell: `avanza10-observed-paper-v1`. Rankningskälla: oförändrad
`avanza10-paper-v2` från PR #41. Kontot återanvänder Qualitys granskade
`RetentionLedger`, bolagshändelser, tidskontroll och oberoende kontoavstämning.
H3, Quality-kontot och historiska simuleringar förblir separata.

## Kapital och urval

Den låsta månadsrankingen styr medlemskap, oberoende av kapital. Samma
emittent förekommer en gång, högst två bolag per SIC-bransch och fyra per
division. Underliggande universum och verifierad företagsdata utesluter ETF:er
från urvalet. SPY ägs endast i ett separat benchmarkkonto.

Startkapital föreslås till 20 000 SEK. Webbläsarens kapitalplan är lokal och
ändrar aldrig automatkontots historik. Repository-variabeln
`AVANZA_INITIAL_SEK` anger automatkontots kapital före initiering; därefter
är kapitalet låst i journalen. Att byta variabel startar inte om ett konto.
Ett nytt konto kräver en ny uttryckligen versionshanterad kohort.

Hela aktier, tio mål, minst en aktie per position. Minimikapital och köpreserv
visas separat: högst 20 % per aktie, 30 % per bransch och 50 % per division.
Kostnadsmodell från den befintliga motorn: minst 1 USD eller 0,25 % courtage
plus 0,40 % av notionalen (0,25 % växling och 0,15 % exekvering). Planer använder
2 % köpgränsbuffert. Detta är modellerade kostnader, inte ett brokerpris.

## Automatiken

`quality_forward.yml` kör 08:17, 14:47, 15:47 och 22:17 UTC på vardagar.
Efter oberoende källkontroll och Avanza-rankning körs `avanza10_forward.py`.
Det nya kontot har egna tillstånd, planer, transaktioner och värderingar.

Första månadsurvalet låses av den befintliga snapshotkoden. Nya positioner
kräver minst 90 % verifierade källor, tio mål, daterad FX, tillräcklig kassa
och befintliga viktgränser. Befintliga kvalificerade positioner behåller sina
antal. Månadsbyte eller RISK OFF avbryter inaktuella köpplaner. RISK OFF
planerar försäljningar; innehav blir inte kontanter förrän observerade
fiktiva försäljningar har bokförts. Ingen individuell stopregel införs.

Exakta antal förbinds före en framtida öppning. En raw öppning med positiv
volym måste observeras i det befintliga tillåtna fönstret 09:30–11:30 New York.
Planens tid måste föregå öppningen. Köpgräns och faktisk kassa kontrolleras,
försäljningar behandlas först. Missade öppningar registreras som gap och
rekonstrueras aldrig. Delvis fyllda korgar visas som granskningsspärrade,
inte som en aktiv fullinvesterad tioaktieportfölj. Riskkontrollen fortsätter.

Fiktiva avslut är observerade öppningspriser med modellerade kostnader, inte
realtids- eller brokerbekräftade fills. Ingen faktisk order skickas.

## Beständighet och verifiering

`avanza-state.json` och `avanza-paper.json` bevaras i samma hashverifierade,
varaktiga releasearkiv som källobservationerna. Publicering till
`quality-observed-snapshots` gör compare-and-swap och verifierar append-only
transaktioner, beslut och värderingar. Den separata Avanza-rapporten fogas
in i samma publicerade källrapport så API:t läser ett atomiskt observationspaket.
Ingen databas raderas och ingen gammal journal skrivs om.

Oberoende `audit_account` rekonstruerar kassa, antal, avgifter, utdelningskrav,
splittar, bolagshändelser och värderingar från journal och observerade kurser.
Senast faktiskt observerade stängning värderas dagligen; missade datum
markeras utan backfill. SEK använder daterad ECB-fix. Affärer efter senaste
stängning ger väntande värdering och inget påhittat NAV. SPY-serien visas bara
om båda separata kontona har jämförbar faktisk paperstart.

Inköpspris och innehavsavkastning visas endast när handelsjournalen förklarar
nuvarande antal. Efter en bolagshändelse som kräver ny kostnadsbasis visas
okänd basis i stället för en felaktig avkastning. Portföljens NAV inkluderar
motorns hantering av bolagshändelser och utdelningsfordringar. Kostnader i SEK
för köp och försäljning omräknas med daterad FX.

API:t faller tillbaka till daterad information med explicit spärr vid
leveransfel. Automatik är verifierad endast med färsk leverans och godkända
oberoende kontoavstämningar. Finansieringsspärr är skild från leveransspärr.

## Ekonomisk status

PAPER ONLY och `NO_GO_INSUFFICIENT_EVIDENCE`. Ingen ekonomisk godkännandegräns
ändras: bland annat 30 fullständiga månader, positiv nettoavkastning,
överavkastning mot SPY, drawdown och positiva månader enligt det frysta
protokollet. Arkivets historiska simuleringar räknas inte som paperhistorik
eller som ekonomiskt godkännande för det nya kontot.

## Verifiering

- Python-sviten inklusive separat kapital-/observations-/retentions-/riskflöde.
- Node-sviten inklusive API:s separering från Quality och säkra tomma lägen.
- Mobil och desktop: samtliga flikar, kapitaländring, arkiv, laddningsfel.
- Actions-körning måste granskas innan faktisk automatik påstås fungera.
