# MomentumCloud — avslutad riskprövning, 29 oktober 2026

**Ingen prövad modell uppfyller samtliga oförändrade GO-krav. Två konkreta riskändringar är byggda och genomprövade. Förbättringar i utvecklingstestet höll inte i den senare kontrollperioden. Ingen modell för riktiga pengar är godkänd.**

Kod: [PR 20](https://github.com/tartkennet/MomentumCloud/pull/20).
Fullföljd prövning: [Actions 40791570390](https://github.com/tartkennet/MomentumCloud/actions/runs/40791570390).
Separat evidensexport: [Actions 40794576905](https://github.com/tartkennet/MomentumCloud/actions/runs/40794576905).

## Faktiska ändringar och flaskhals

research_core_stop.py testar v4:s befintliga 10-procentiga stopp mot viktat faktiskt inköpspris. research_core_trailing.py testar samma tröskel mot högsta observerade stängning sedan köp. Signalen bildas vid stängning och försäljningen sker vid nästa verkliga öppning. Sålda kapitalandelar lämnas i kassa och återköp samma månad blockeras. Splitar, tickerbyten, stock/cash mergers och hela aktier hanteras i handelsboken.

Urval, 12–2-rankning, universum, pris- och likviditetsgränser, SPY-regim, viktning och godkännandekrav har inte lättats. Core fyllde alla 15 målplatser vid samtliga 34 RISK ON-rankningar i den förlängda baslinjen, med 845–1 713 kvalificerade kandidater. Tomt urval är inte flaskhalsen i Core. Den äldre dashboardens Buy Now är en separat kedja.

Första riskvarianten frystes i 93e06fd79610a1c08984b93d2bf387859dce8af6. Den andra hypotesen och jämförelsen frystes i 19032b041a972f5b6916c13ef60bdd8feb1ab022 före granskning av förlängningens utfall. Inga riskparametrar ändrades för att passa den senare perioden.

## Utvecklingsperioden: 2024-01-01–2026-09-01

Tabellen använder samma **antagna fem handelssessioners betalningsfördröjning** för alla modeller. Det är inte verifierade verkliga betalningsdagar. Alla fem betalningspolicyer och båda kostnaderna redovisas också.

| Modell, 15 bp/sida | Netto | SPY | Maximal nedgång | Missade krav |
|---|---:|---:|---:|---|
| Core original | 25,51 % | 65,44 % | -47,38 % | beats_spy, drawdown |
| 10 % inköpsstopp | 66,89 % | 65,44 % | -33,14 % | drawdown |
| 10 % rörligt stopp | 70,25 % | 65,44 % | -28,88 % | drawdown |

Vid dubbla kostnader, 30 baspunkter per sida, fallerar även SPY-jämförelsen för båda riskvarianterna i detta femsessionsfall. Ingen betalningspolicy väljs ut för att få grönt resultat.

## Senare kontrollperiod: 2 september–28 oktober 2026

Samma konton återstartades från sparat tillstånd den 1 september, utan nytt kapital eller nollställda innehav. 40 nya observerade sessioner ingår.

| Modell, 15 bp/sida | Netto 2 sep–28 okt | SPY | Faktiska simuleringsavgifter |
|---|---:|---:|---:|
| Core original | -7,89 % | 1,59 % | 220.49 USD |
| 10 % inköpsstopp | -15,56 % | 1,59 % | 593.99 USD |
| 10 % rörligt stopp | -15,29 % | 1,59 % | 863.24 USD |

Perioden är inte certifierat orörd holdout och inte framåtriktad paper. Tidigare projektarbete såg aktuella marknadssnapshots. Här finns bara ett komplett månadsintervall och en ofullständig slutmånad, inte 30 nya oberoende observationer. Riskändringarna gav inget robust godkännande i denna kontroll.

## Sammanhängande konto till 28 oktober 2026

709 dagsvärden och 33 kompletta månadsintervall:

| Modell, 15 bp/sida | Netto | SPY | Maximal nedgång | Missade krav |
|---|---:|---:|---:|---|
| Core original | 15,60 % | 68,08 % | -47,38 % | beats_spy, drawdown |
| 10 % inköpsstopp | 40,92 % | 68,08 % | -33,14 % | beats_spy, drawdown |
| 10 % rörligt stopp | 44,22 % | 68,08 % | -28,88 % | beats_spy, drawdown |

Gränserna i momentum_core.py::gates är oförändrade: minst 30 kompletta perioder, positiv nettoavkastning, positiv avkastningsskillnad mot SPY, daglig maximal nedgång minst −20 %, och minst 50 % positiva månadsperioder. run_core_risk_research.py skriver separata beslutsfiler. Historiska pass skulle vara PAPER_ONLY. live_approved=false och broker_orders_enabled=false kvarstår.

## Konkreta riskorsaker

Oberoende P&L-attribution av den tidigare baslinjens femsessionsfall stämmer av topp-till-botten-förlusten 68 692,86 USD. RNA, EBS, CATX, RDW och RKLB är exempel på negativa bidrag. Dessa namn utesluts inte i efterhand.

Stoppnivån är inget garanterat pris. LUNR gick från signalstängning 11,26 USD den 6 mars 2025 till nästa observerade öppning 7,26 USD, cirka 35,52 % lägre. ERAS gick i den rörliga varianten från signalstängning 19,15 USD till öppning 10,51 USD den 28 april 2026, cirka 45,12 % lägre. Handelsboken använder de observerade öppningspriserna. [SEC beskriver denna begränsning med stoporder](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15).

## Verifiering och rättningar

- 163 funktionstester passerar.
- 60 konton/scenarier är fullföljda: tre modellfamiljer × fem betalningspolicyer × två kostnader i två faser. Detta är inte 60 oberoende marknadsurval.
- Samtliga 60 har separat kass-/aktie-/fordrings-/avgiftskontroll, med 0 USD största NAV-avvikelse.
- Separat policykontroll importerar inte riskmotorerna och verifierar 40 riskkonton, 11 630 signaler och 11 610 försäljningar vid nästa session.
- Offlineåterkörningen reproducerar ekonomiska mått och gates; 360 dags-/affärs-/period-/mål-/tillstånds-/checkpointfiler är identiska med den första fullständiga prövningen.
- Ett rapportfel rättades: förlängningens separata avgiftsfält hade blivit noll genom en temporär måttbehållare. Fältet visar nu verklig avgiftsökning. Nettoavkastning, hela kontots avgifter, affärer och gates ändrades inte. Alla andra runnerfunktioner och båda frysta riskmodulerna är oförändrade.
- En senare utdelningscache stoppades av indatahashkontrollen trots identiska grundmått. Originalvintagen återställdes. PR-scopade cacher ersätts som långtidskälla av ett opublicerat krypterat forskningspaket.

1 001 indatafiler är hashverifierade. Samtliga 957 ursprungliga filer är oförändrade; 44 filer har tillkommit. Sparade råprissessioner omfattar 2022-12-29–2026-10-28. Detta är inte en export av alla oanvända fem abonnemangsår.

Ursprungligt källfingeravtryck: c88761ba2ca70c42298a647b641a3f5e4a98fcb6592f0b76d7817daaee1008e2.
Forskningsfingeravtryck: f1ed81a24d0ba988314cc8e958e0ed42a16aba34ca5e7527bd4f1a39c66649c1.

## Kvarstående blockerare och A–F

A. **Tekniskt färdigt för riktiga pengar: NEJ.** Forskningsmotor, bevarande och kontroller fungerar. Ekonomiskt godkännande och verklig exekvering saknas.

B. **PIT-universum:** datumstyrda common-stock-register används. Leverantörens ursprungliga historiska datavintage och alla instrumentidentiteter är inte oberoende certifierade.

C. **Survivorship bias:** dagens Excel-lista används inte som historiskt universum. Senare avnoterade innehav ingår. Leverantörsbackfill kvarstår som begränsning.

D. **Corporate actions:** observerade händelser är bokförda och avstämda. Faktiska betalningsdagar för åtta mergerfordringar är fortfarande inte verifierade. 0/1/5/20-sessionsscenarierna är antaganden.

E. **Likviditet:** 5 miljoner USD i ADV20 och antagen 15/30 bp-kostnad bevisar inte öppningslikviditet eller faktisk slippage.

F. **Logisk felräkning:** ingen separat avstämd NAV-avvikelse undanröjer kraven. Avgiftsrapportfältet är rättat. Risk och senare underprestation kvarstår.

Core-paper-identiteten och v4-dashboarden är inte omdöpta till godkända signaler. Riskvarianterna är forskningskod. Alla försök och missade gates bevaras. Inga krav sänks i efterhand för att kalla modellen GO.

## Bevarade filer

Det opublicerade forskningspaketet core-risk-research-20261029 bevarar krypterade indata, exakt kod, resultat och hashmanifest. Exporten kompletterar det med mottagarkrypterade indata och verifierade resultat. Ingen API-nyckel publiceras. Det tidigare privata datapaketet i ChatGPT innehåller mottagarnyckeln för att öppna mottagarkrypterade exporter. Själva offlineberäkningen kräver inget nytt historikabonnemang.

## Alla fasta scenarier

| Fas | Variant/policy | Kostnad/sida | Netto | Maximal nedgång | Missade krav |
|---|---|---:|---:|---:|---|
| historical | baseline_locked_15bps | 15 bp | 44,31 % | -37,52 % | beats_spy, drawdown |
| historical | baseline_locked_30bps | 30 bp | 39,54 % | -37,87 % | beats_spy, drawdown |
| historical | baseline_assumed_0_15bps | 15 bp | 25,46 % | -47,39 % | beats_spy, drawdown |
| historical | baseline_assumed_0_30bps | 30 bp | 19,69 % | -47,95 % | beats_spy, drawdown |
| historical | baseline_assumed_1_15bps | 15 bp | 25,51 % | -47,38 % | beats_spy, drawdown |
| historical | baseline_assumed_1_30bps | 30 bp | 19,58 % | -47,96 % | beats_spy, drawdown |
| historical | baseline_assumed_5_15bps | 15 bp | 25,51 % | -47,38 % | beats_spy, drawdown |
| historical | baseline_assumed_5_30bps | 30 bp | 19,58 % | -47,96 % | beats_spy, drawdown |
| historical | baseline_assumed_20_15bps | 15 bp | 26,73 % | -47,34 % | beats_spy, drawdown |
| historical | baseline_assumed_20_30bps | 30 bp | 21,63 % | -47,95 % | beats_spy, drawdown |
| historical | stop10_locked_15bps | 15 bp | 70,90 % | -28,09 % | drawdown |
| historical | stop10_locked_30bps | 30 bp | 63,53 % | -28,75 % | beats_spy, drawdown |
| historical | stop10_assumed_0_15bps | 15 bp | 66,54 % | -33,15 % | drawdown |
| historical | stop10_assumed_0_30bps | 30 bp | 57,50 % | -33,95 % | beats_spy, drawdown |
| historical | stop10_assumed_1_15bps | 15 bp | 66,77 % | -33,20 % | drawdown |
| historical | stop10_assumed_1_30bps | 30 bp | 57,55 % | -33,95 % | beats_spy, drawdown |
| historical | stop10_assumed_5_15bps | 15 bp | 66,89 % | -33,14 % | drawdown |
| historical | stop10_assumed_5_30bps | 30 bp | 57,55 % | -33,95 % | beats_spy, drawdown |
| historical | stop10_assumed_20_15bps | 15 bp | 71,07 % | -33,14 % | drawdown |
| historical | stop10_assumed_20_30bps | 30 bp | 61,42 % | -33,90 % | beats_spy, drawdown |
| historical | trailing10_locked_15bps | 15 bp | 53,89 % | -25,62 % | beats_spy, drawdown |
| historical | trailing10_locked_30bps | 30 bp | 42,90 % | -28,05 % | beats_spy, drawdown |
| historical | trailing10_assumed_0_15bps | 15 bp | 69,31 % | -29,33 % | drawdown |
| historical | trailing10_assumed_0_30bps | 30 bp | 56,01 % | -31,94 % | beats_spy, drawdown |
| historical | trailing10_assumed_1_15bps | 15 bp | 69,28 % | -29,31 % | drawdown |
| historical | trailing10_assumed_1_30bps | 30 bp | 56,01 % | -31,93 % | beats_spy, drawdown |
| historical | trailing10_assumed_5_15bps | 15 bp | 70,25 % | -28,88 % | drawdown |
| historical | trailing10_assumed_5_30bps | 30 bp | 56,73 % | -31,50 % | beats_spy, drawdown |
| historical | trailing10_assumed_20_15bps | 15 bp | 70,08 % | -28,62 % | drawdown |
| historical | trailing10_assumed_20_30bps | 30 bp | 56,49 % | -31,30 % | beats_spy, drawdown |
| extension | baseline_locked_15bps | 15 bp | 37,31 % | -37,52 % | beats_spy, drawdown |
| extension | baseline_locked_30bps | 30 bp | 32,20 % | -37,87 % | beats_spy, drawdown |
| extension | baseline_assumed_0_15bps | 15 bp | 15,55 % | -47,39 % | beats_spy, drawdown |
| extension | baseline_assumed_0_30bps | 30 bp | 10,37 % | -47,95 % | beats_spy, drawdown, hit_rate |
| extension | baseline_assumed_1_15bps | 15 bp | 15,60 % | -47,38 % | beats_spy, drawdown |
| extension | baseline_assumed_1_30bps | 30 bp | 10,28 % | -47,96 % | beats_spy, drawdown, hit_rate |
| extension | baseline_assumed_5_15bps | 15 bp | 15,60 % | -47,38 % | beats_spy, drawdown |
| extension | baseline_assumed_5_30bps | 30 bp | 10,28 % | -47,96 % | beats_spy, drawdown, hit_rate |
| extension | baseline_assumed_20_15bps | 15 bp | 16,39 % | -47,34 % | beats_spy, drawdown |
| extension | baseline_assumed_20_30bps | 30 bp | 11,98 % | -47,95 % | beats_spy, drawdown, hit_rate |
| extension | stop10_locked_15bps | 15 bp | 51,08 % | -28,09 % | beats_spy, drawdown |
| extension | stop10_locked_30bps | 30 bp | 44,75 % | -28,75 % | beats_spy, drawdown |
| extension | stop10_assumed_0_15bps | 15 bp | 40,97 % | -33,15 % | beats_spy, drawdown |
| extension | stop10_assumed_0_30bps | 30 bp | 32,78 % | -33,95 % | beats_spy, drawdown |
| extension | stop10_assumed_1_15bps | 15 bp | 40,80 % | -33,20 % | beats_spy, drawdown |
| extension | stop10_assumed_1_30bps | 30 bp | 32,83 % | -33,95 % | beats_spy, drawdown |
| extension | stop10_assumed_5_15bps | 15 bp | 40,92 % | -33,14 % | beats_spy, drawdown |
| extension | stop10_assumed_5_30bps | 30 bp | 32,83 % | -33,95 % | beats_spy, drawdown |
| extension | stop10_assumed_20_15bps | 15 bp | 44,49 % | -33,14 % | beats_spy, drawdown |
| extension | stop10_assumed_20_30bps | 30 bp | 36,40 % | -33,90 % | beats_spy, drawdown |
| extension | trailing10_locked_15bps | 15 bp | 37,92 % | -25,62 % | beats_spy, drawdown |
| extension | trailing10_locked_30bps | 30 bp | 27,75 % | -28,05 % | beats_spy, drawdown |
| extension | trailing10_assumed_0_15bps | 15 bp | 43,39 % | -29,33 % | beats_spy, drawdown |
| extension | trailing10_assumed_0_30bps | 30 bp | 31,51 % | -31,94 % | beats_spy, drawdown |
| extension | trailing10_assumed_1_15bps | 15 bp | 43,37 % | -29,31 % | beats_spy, drawdown |
| extension | trailing10_assumed_1_30bps | 30 bp | 31,51 % | -31,93 % | beats_spy, drawdown |
| extension | trailing10_assumed_5_15bps | 15 bp | 44,22 % | -28,88 % | beats_spy, drawdown |
| extension | trailing10_assumed_5_30bps | 30 bp | 32,09 % | -31,50 % | beats_spy, drawdown |
| extension | trailing10_assumed_20_15bps | 15 bp | 44,08 % | -28,62 % | beats_spy, drawdown |
| extension | trailing10_assumed_20_30bps | 30 bp | 31,88 % | -31,30 % | beats_spy, drawdown |
