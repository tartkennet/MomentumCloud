# Portföljrisk efter PR #23

## Verifierad orsak

Analysen återanvänder PR #23:s färdiga konto, inga gamla strategier körs om. Oberoende innehavsrekonstruktion förklarar varje dags NAV-förändring med positionernas netto-P&L, inklusive kostnader, aktiebyten, kontanter, utdelningar och avknoppningar. Samtliga 709 sessioner stämmer, maximal differens 6,37e-11 USD. De 1001 ursprungliga datafilerna är oförändrade.

| Topp till botten | Portfölj | SPY | Risk-on-andel | Största negativa positionsbidrag USD |
|---|---:|---:|---:|---|
| 2026-06-22–2026-10-16 | −36,26 % | +2,72 % | 100 % | WDC −12 338, VICR −8 847, ANRO −8 645, STX −7 873, BW −7 813, SNDK −7 736 |
| 2024-11-11–2025-05-13 | −32,43 % | −1,37 % | 66,1 % | ZETA −6 388, FTAI −6 232, RNA −5 206, WLFC −4 894, RDW −4 535 |
| 2025-10-15–2025-12-17 | −24,47 % | +0,92 % | 100 % | RGTI −8 248, RKLB −6 535, QBTS −6 501, QUBT −5 003, AMPX −4 450 |

Det är inte främst ett enskilt överstort innehav: under den största nedgången finns minst 12,4 effektiva aktier och största vikt är 12,3 %. Gemensamma riskkluster är däremot betydande. WDC/STX/SNDK utgör tillsammans 31,19 % av NAV vid juni-toppen och 24,31 % av periodens nettoförlust. RGTI/QBTS/QUBT står för 41,02 % av hösten 2025:s nettoförlust. ARMN/SSRM/AU/KGC/HYMC/HL utgör 46,37 % vid toppen 2026-01-28 och förklarar 80,16 % av nedgången till januari månads slut. Detta är diagnostiska tickergrupper beräknade i efterhand, inga urvalsfilter.

34 risk-on-signaler av totalt 37 har fullständig riskberäkning. Den befintliga 63-dagarsberäkningen visar 1,14–4,56 gånger SPY:s volatilitet, median 2,89. Invers volatilitet per position jämnar ut risk mellan aktier men sätter inget tak på portföljens samlade risknivå. Den 2026-07-01 är beräknad annualiserad portföljvolatilitet 62,4 % mot SPY 13,7 %, viktad parkorrelation 0,378 och korrelation mot SOXX 0,832. I augusti är SOXX-korrelationen 0,861. Den sämsta dagen, 2026-06-05, är −10,72 % med samtidiga förluster i flera positioner.

SPY:s trendregim skiljer inte bort dessa portföljspecifika risker. Sektorliknande kluster och hög total risk är därför mer välgrundade förklaringar än ett nytt generellt marknadsfilter. Sparat point-in-time-register saknar sektor/SIC, vilket begränsar en full historisk sektorklassificering. SOXX är en verifierad halvledarproxy ([fondutgivaren](https://www.ishares.com/us/products/239705/SOX)); dess korrelation är ingen formell klassificering av portföljens aktier och inget bevis på kausalitet.

Fulla åtta icke överlappande nedgångsepisoder, dagliga innehavsvikter, riskbidrag och sektorfondskorrelationer är bevarade i Actions 40858434977 och draft-release `core-portfolio-diagnosis-40858434977`. ZIP SHA256: `c12d7cd081badd809cdaea79168967344cb7a8c8f9fda53b728faa92f63a83d7`.

## Förregistrerade försök

H1 frystes i `1fbb2c9087aa8af94df106d65d1236e3d9ab2723` före resultatberäkning. Regeln multiplicerar samma ursprungliga aktievikter med min(1, SPY:s standardavvikelse / aktiekorgens standardavvikelse), från samma befintliga 63 observationer, och behåller resten i kassa. Ingen ny risknivå eller period söks. Kod och oberoende kovariansrevisor frystes i `8ed816f77462c33b90af0c52f0f1f0046b13a544`. Medianexponeringen som regeln ger vid dessa signaler är 34,61 %.

Förtydligande till H1-protokollet: det finns 37 signaler totalt, varav 34 risk-on-signaler med en aktiekorg och därmed en beräknad riskkvot. Detta ändrar varken hypotes eller beräkning.

H1:s samtliga 40 konton är COMPLETE, oberoende kontroller PASS och finansiellt NO_GO för SPY-kravet. Primärfallet ger +51,55 %, drawdown −14,18 %, Sharpe 1,148 och 2639,02 USD kostnader. Daglig genomsnittlig aktieexponering är 33,87 %. Alla 40 CSV-exporters avkastning, drawdown och Sharpe har dessutom räknats om lokalt efter verifierad ZIP-hash `90bf4b7957754ac7d3015b29a52254c31c9904ce996956ab766e7e8dd3cb7b08`. Resultaten är bevarade i Actions 40859366045 och draft-release `core-portfolio-h1-40859366045`.


H2 frystes i `8f78ba88ffe84fae0165f4d3d1e4c0370914be3f` före resultat. En bred SPY-kärna och den oförändrade momentumkorgen får lika beräknade riskbidrag, utan vald fast kapitalfördelning. Median vid risk-on-signalerna är 25,71 % momentum och 74,29 % SPY. Samtliga 40 konton är tekniskt PASS men NO_GO för drawdown. Primärfallet ger +90,63 %, −21,14 %, Sharpe 1,371 och 2391,78 USD avgifter. 30 bp ger +87,39 %, −21,28 % och fortsatt NO_GO. De 40 exporterade kontonas avkastning, SPY, drawdown och Sharpe har också räknats om separat lokalt. ZIP SHA256: `e7cae32f0830cd1f83e14667217387039c7246ef259164de8ec7fbdff1623492`. Fulla resultat och källor finns i Actions 40861070577 och draft-release `core-portfolio-h2-40861070577`.

H2:s återstående största nedgång är 2025-02-18–2025-04-08, 31 122,99 USD. SPY-kärnan bidrar med −17 750,90 USD och övriga positioner med −13 372,08 USD. 20 av 35 sessioner från topp till botten har risk-off vid stängning. Samma stängning används inte som säljkurs: en full replay krävs för att pröva vad som kan undvikas vid nästa verkliga öppning. [Kärnattributionen](CORE_PORTFOLIO_H2_CORE_ATTRIBUTION_20261029.json) är reproducerbar med `attribute_benchmark_core.py` från de redan reviderade kontoutdragen. H3 förregistrerar därför konsekvent tillämpning av det befintliga marknadsbeslutet på båda aktiedelarna; ingen riskgräns ändras.
