# Slutverifiering av PR #22 och en förregistrerad förbättring

Status: tekniskt PASS, finansiellt NO_GO. Ingen produktionsmodell har bytts ut och inga broker-order aktiverats.

## Genomförande och reproducerbara bevis

- PR #22 är sammanslagen i `30f19d8936fbdee60888d6d1d9a1c7430c78d621`. Den fullständiga replayen kördes från `41952be9e54c40cb3456bd75ce13155e785a4689`: [Actions 40849825735](https://github.com/tartkennet/MomentumCloud/actions/runs/40849825735). Samtliga 40 konton är COMPLETE, bokförings- och urvalskontroller PASS; samtliga finansiellt NO_GO.
- Den enda förbättringens hypotes frystes i `350e16c77087bd7e1a81b54cb9f8aa88d625799a` före resultatberäkning. Full replay från `333805e4c570ee6fa0ec7574154d53fff3425471`: [Actions 40853780420](https://github.com/tartkennet/MomentumCloud/actions/runs/40853780420). Samtliga 40 konton är COMPLETE, bokförings- och urvalskontroller PASS; samtliga finansiellt NO_GO. NGD:s verifierade byte till 0,4959 CDE kompletterade historisk bokföring före denna replay.
- Varje studie innehåller två värderingsregler för det bekräftade PLYA-stoppet, fem betalningsantaganden, 15/30 bp kostnad och två historiska faser. Samma sparade konton återupptas efter 2026-09-01 till 2026-10-28. Ingen historisk equity, transaktion eller målrad ändras vid återupptagning.
- Samtliga 1001 sparade rådatafiler hashkontrolleras före och efter; nätverksanslutning är blockerad i replayprocessen. Tidigare Core och den färdiga normaliserade modellen återanvänds från hashkontrollerade resultat; deras analyser körs inte om.
- Fulla källarkiv, resultat, loggar och SHA256-manifest finns beständigt i draft-releaserna `core-normalized-research-40849825735` och `core-formation-research-40853780420`. Artifact ZIP SHA256 är respektive `f8cb04f48b115f600febefd8ec6f8299c5a70e9951dc8d70a2515b60c1a5adde` och `7a97b2e51327fdf35bd9c8355ba06da636b64f0f2217acb524ccf4f5538b5339`.

## Oberoende kontroll

Den separata revisorn rekonstruerar råpriser, faktiska next-open-affärer, heltal och kvarvarande fraktioner, aktiebyten, kontantfordringar, utdelningar, avknoppningen, suspensionens värdering, kostnader, SPY, dagligt NAV, avkastning och drawdown utan att anropa replay, ledger eller produktionsmått. Maximal NAV-differens är 2,91e-11 USD för PR #22 och 0 USD för uppföljningen. Primärfallet omfattar 709 sessioner och 743 respektive 732 transaktionsrader.

Urvalsrevisorn rekonstruerar signaler, point-in-time-urval, ranking, vikter och nästa observerade handelsöppning. Primärfallen har 37 signaler och 45 891 kontrollerade kandidatposter vardera. En ytterligare lokal kontroll efter nedladdning verifierade båda ZIP-hasharna och räknade separat om nettoavkastning, SPY-avkastning, drawdown och Sharpe från alla 80 exporterade dagliga CSV-filer; samtliga överensstämmer. Dessa är oberoende implementationer på samma leverantörsdata, inte en andra marknadsdatakälla eller bevis på alpha.

## Jämförbara resultat

Gemensam period 2024-01-01–2026-10-28, USD efter kostnader, före skatt. Tabellen visar det fördefinierade fallet med 15 bp per sida, antagen betalning efter fem observerade sessioner och senaste observerade kurs under PLYA:s handelsstopp. Betaldatum är en känslighetsanalys, inte verifierade faktiska kontantbetalningar.

| Modell | Nettoavkastning | Maximal drawdown | Daglig Sharpe, RF=0 | Kostnader USD |
|---|---:|---:|---:|---:|
| Tidigare Core | +15.60 % | -47.38 % | 0.347 | 5701.84 |
| Normaliserad ranking, PR #22 | +62.48 % | -20.94 % | 0.843 | 6550.67 |
| Samma formationsperiod för avkastning och risk | +129.48 % | -36.26 % | 0.920 | 9014.98 |
| SPY | +68.08 % | -18.49 % | 1.293 | 149.60 |


Daglig Sharpe använder enkla USD-dagsavkastningar, stickprovsstandardavvikelse, noll riskfri ränta och annualisering med sqrt(252). Avgifterna är faktiska simulerade kostnader på omsatt belopp. Dubbel kostnad är 30 bp per sida; uppföljningens primärfall ger då +118,46 %, drawdown −36,68 % och fortsatt NO_GO.

| Kalenderperiod | Tidigare Core | PR #22 | Gemensam formationsrisk | SPY |
|---|---:|---:|---:|---:|
| 2024 | +8.90 % | +25.86 % | +57.02 % | +25.87 % |
| 2025 | -12.44 % | +14.52 % | -1.97 % | +17.37 % |
| 2026 | +21.24 % | +12.73 % | +49.08 % | +13.77 % |

Den separat återupptagna perioden 2026-09-02–2026-10-28 omfattar 40 sessioner: PR #22 −2,50 %, uppföljningen −7,60 %, SPY +1,59 %. Uppföljningens drawdown inom segmentet är −21,31 %. Fullständiga Sharpe-, kostnads- och drawdownuppdelningar finns i respektive JSON-register och `diagnostics.json` i resultatarkiven.

## Slutsats och återstående verifierade svaghet

PR #22 fallerar SPY-kravet och drawdowngränsen på −20 %. Den verifierade nämnarsvagheten dokumenteras i [förbättringens förregistrerade protokoll](CORE_FORMATION_RISK_PROTOCOL_20261029.md): en äldre uppköpsrelaterad kursökning kan ligga kvar i 12–2-avkastningen men ha fallit ur den korta riskperioden. Exakt en förändring testades: rankingen använder risk över samma befintliga formationsperiod. Storleksregler, universum, marknadsfilter, tidpunkter och samtliga fem GO-gränser behölls.

Förändringen höjer utvecklingsavkastningen men löser inte portföljrisken. Alla 40 uppföljningsfall fallerar drawdown; det bästa drawdownutfallet bland dem är fortfarande sämre än −31 %. I primärfallet faller NAV från 316 968,36 USD den 2026-06-22 till 202 030,21 USD den 2026-10-16, −36,26 %. SPY stiger ungefär 2,72 % mellan dessa två datum och urvalsloggen har enbart risk-on-signaler under intervallet. Aktieexponeringen är cirka 97,63 % respektive 99,05 % vid dessa ändpunkter. Det visar att SPY:s marknadsfilter inte begränsar den här portföljens specifika nedgång till GO-gränsen. Detta är ett verifierat riskproblem; någon ny risknivå har inte sökts fram ur utfallet.

Underkända forskningars kod och bevis bevaras separat. Original-Core-källidentiteten är oförändrad: `c88761ba2ca70c42298a647b641a3f5e4a98fcb6592f0b76d7817daaee1008e2`. Forskningsworkflowen är manuellt reproducerbara efter avslutad validering så att rapportuppdateringar inte startar samma experiment på nytt.

## Out-of-sample-status

Det finns ingen orörd historisk holdout i de redan granskade sparade uppgifterna. Den senare perioden redovisas separat men betecknas inte som verklig out-of-sample. Ingen framtida avkastning eller ny kandidats paper-historik har konstruerats. Befintlig fryst Core-paper får samla faktiska framtida sessioner enligt sitt redan beslutade protokoll; dess resultat kan inte tillskrivas dessa ändrade regler. Därmed är någon fullständig out-of-sample-validering av forskningskandidaterna inte genomförd. Båda är dessutom redan historiskt NO_GO och har inte ersatt produktionsmodellen.
